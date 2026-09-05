import type { State } from "./api";
const clock = (n: number) =>
  `${String(Math.floor(n / 60)).padStart(2, "0")}:${String(n % 60).padStart(2, "0")}`;
const mins = (s: FormDataEntryValue | null) => {
  const [h, m] = String(s).split(":").map(Number);
  return h * 60 + m;
};
export function WeeklyRhythm({
  state,
  act,
  busy,
}: {
  state: State;
  act: (name: string, data?: unknown) => Promise<unknown>;
  busy: boolean;
}) {
  const r = state.settings.weeklyRhythm;
  if (!r) return null;
  return (
    <form
      className="card"
      onSubmit={(e) => {
        e.preventDefault();
        const d = new FormData(e.currentTarget);
        act("settings", {
          screenWorkEnd: mins(d.get("screenWorkEnd")),
          inBedBy: mins(d.get("inBedBy")),
          weeklyRhythm: {
            workStart: mins(d.get("workStart")),
            workEnd: mins(d.get("workEnd")),
            eveningStart: mins(d.get("eveningStart")),
            eveningEnd: mins(d.get("eveningEnd")),
            weekendStart: mins(d.get("weekendStart")),
            weekendEnd: mins(d.get("weekendEnd")),
            eveningDays: d.getAll("eveningDays").map(Number),
          },
        });
      }}
    >
      <h2>Work, evenings and weekends</h2>
      <p>
        Employment work uses Monday to Friday. Your own projects use the
        personal windows. Empty time is available space, not an obligation to
        fill it.
      </p>
      {(
        [
          ["work", "Employment work"],
          ["evening", "Personal evenings"],
          ["weekend", "Personal weekend time"],
        ] as const
      ).map(([key, label]) => (
        <div key={key}>
          <h3>{label}</h3>
          <div className="form-row">
            <label>
              From
              <input
                type="time"
                name={key + "Start"}
                required
                defaultValue={clock(r[`${key}Start`])}
              />
            </label>
            <label>
              Until
              <input
                type="time"
                name={key + "End"}
                required
                defaultValue={clock(r[`${key}End`])}
              />
            </label>
          </div>
        </div>
      ))}
      <div className="form-row">
        <label>
          Stop screen work
          <input
            type="time"
            name="screenWorkEnd"
            required
            defaultValue={clock(state.settings.screenWorkEnd || 1320)}
          />
        </label>
        <label>
          In bed by
          <input
            type="time"
            name="inBedBy"
            required
            defaultValue={clock(state.settings.inBedBy || 1380)}
          />
        </label>
      </div>
      <fieldset>
        <legend>Evenings available for your projects</legend>
        {["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"].map(
          (day, i) => (
            <label className="meeting-check" key={day}>
              <input
                type="checkbox"
                name="eveningDays"
                value={i}
                defaultChecked={r.eveningDays.includes(i)}
              />
              {day}
            </label>
          ),
        )}
      </fieldset>
      <button className="primary" disabled={busy}>
        Save weekly rhythm
      </button>
    </form>
  );
}
