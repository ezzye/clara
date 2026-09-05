import unittest
from datetime import datetime
from apps.api.domain import initial_state, event_from, propose_plan, public_state, TZ
from apps.api.meetings import edit, set_status, review, preparation, protect


class MeetingPreparation(unittest.TestCase):
    def setUp(self):
        self.state = initial_state()
        self.current = datetime(2026, 9, 7, 8, tzinfo=TZ)
        self.event = event_from({'title': 'Design review', 'date': '2026-09-08', 'start': 540, 'prepMinutes': 30})
        self.state['events'].append(self.event)

    def plan(self, days=2):
        self.state['plan'], warnings = propose_plan(self.state, '2026-09-07', days, current=self.current)
        return warnings

    def test_morning_meeting_prepared_previous_day(self):
        self.plan()
        prep = next(b for b in self.state['plan'] if b['kind'] == 'prep')
        self.assertEqual(prep['date'], '2026-09-07')
        self.assertLessEqual(prep['start'] + prep['minutes'], 1020)
        status = preparation(self.event, self.state['plan'], self.current)
        self.assertEqual(status['status'], 'reserved')
        self.assertFalse(self.event.get('prepared', False))

    def test_all_appointments_protected_before_preparation(self):
        self.event.update(date='2026-09-07', start=600)
        self.state['events'].append(event_from({'title': 'Earlier call', 'date': '2026-09-07', 'start': 550, 'minutes': 30, 'prepMinutes': 0}))
        self.plan(1)
        prep = [b for b in self.state['plan'] if b['kind'] == 'prep']
        self.assertEqual(prep, [])  # No full slot between working-day start and call.

    def test_fallback_to_earlier_free_gap(self):
        self.event.update(date='2026-09-07', start=720)
        self.state['events'].append(event_from({'title': 'Earlier call', 'date': '2026-09-07', 'start': 670, 'minutes': 40, 'prepMinutes': 0}))
        self.plan(1)
        prep = next(b for b in self.state['plan'] if b['kind'] == 'prep')
        self.assertLessEqual(prep['start'] + prep['minutes'], 660)

    def test_never_invent_preparation_in_past(self):
        self.current = datetime(2026, 9, 7, 16, 50, tzinfo=TZ)
        self.assertTrue(self.plan())
        self.assertFalse(any(b['kind'] == 'prep' for b in self.state['plan']))

    def test_replanning_does_not_duplicate_locked_or_completed_prep(self):
        self.plan()
        prep = next(b for b in self.state['plan'] if b['kind'] == 'prep')
        prep['locked'] = True
        self.plan()
        self.assertEqual(len([b for b in self.state['plan'] if b['kind'] == 'prep']), 1)
        prep = next(b for b in self.state['plan'] if b['kind'] == 'prep')
        prep['status'] = 'done'
        self.plan()
        self.assertEqual(len([b for b in self.state['plan'] if b['kind'] == 'prep']), 1)
        self.assertFalse(self.event.get('prepared', False))
        self.assertEqual(preparation(self.event, self.state['plan'], self.current)['status'], 'review')

    def test_cancel_preserves_history_and_releases_reservations(self):
        self.plan()
        prep = next(b for b in self.state['plan'] if b['kind'] == 'prep')
        prep['status'] = 'done'
        set_status(self.state, {'id': self.event['id'], 'status': 'cancelled'})
        self.plan()
        self.assertEqual(len(self.state['plan']), 1)
        self.assertEqual(self.state['plan'][0]['status'], 'done')
        self.assertEqual(preparation(self.event, self.state['plan'], self.current)['status'], 'cancelled')
        set_status(self.state, {'id': self.event['id'], 'status': 'scheduled'})
        self.assertEqual(sum(b['kind'] == 'event' for b in self.state['plan']), 1)

    def test_move_event_does_not_leave_old_locked_blocks(self):
        self.plan()
        self.event['prepared'] = True
        edit(self.state, {'id': self.event['id'], 'date': '2026-09-09', 'start': 660})
        self.assertFalse(self.event['prepared'])
        self.assertEqual(len(self.state['plan']), 1)
        self.assertEqual(self.state['plan'][0]['date'], '2026-09-09')
        self.assertEqual(self.state['plan'][0]['start'], 660)

    def test_notes_do_not_confirm_details_or_readiness(self):
        review(self.state, {'id': self.event['id'], 'notes': 'Draft questions'})
        self.assertFalse(self.event['confirmed'])
        self.assertFalse(self.event.get('prepared', False))
        review(self.state, {'id': self.event['id'], 'notes': 'Read the design.', 'confirmed': True, 'prepared': True})
        self.assertEqual(preparation(self.event, [], self.current)['status'], 'ready')

    def test_conflict_is_visible_when_new_appointment_added(self):
        protect(self.state, self.event)
        other = event_from({**self.event, 'title': 'Overlapping call'})
        protect(self.state, other)
        self.assertIn('overlaps', self.state['planner']['message'])

    def test_unauthenticated_cannot_change_appointments(self):
        from apps.api.service import dispatch
        for name in ('editEvent', 'eventStatus', 'saveMeeting'):
            with self.assertRaises(PermissionError):
                dispatch(None, '/api/action', 'POST', {'action': name}, owner=False)

    def test_background_adds_tomorrow_prep_without_moving_focus(self):
        import tempfile
        from unittest.mock import patch
        from apps.api.storage import Store
        from apps.api.scheduler import scheduled
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(tmp)
            block = {'id': 'protected-work', 'title': 'Work', 'date': '2026-09-07', 'start': 600, 'minutes': 25, 'status': 'planned', 'kind': 'project', 'locked': False}
            self.state['plan'] = [block.copy()]
            store.write(self.state, 0)
            with patch('apps.api.scheduler.datetime') as clock:
                clock.now.return_value = self.current
                result = scheduled(store)
                self.assertTrue(result['preparationOnly'])
                saved = store.read()
                self.assertEqual(next(b for b in saved['plan'] if b['id'] == block['id']), block)
                self.assertEqual(sum(b['kind'] == 'prep' for b in saved['plan']), 1)
                self.assertTrue(scheduled(store)['unchanged'])
