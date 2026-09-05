import { useState } from "react";
import { ArrowRight, Check } from "lucide-react";
import type { State } from "./api";
type Project = State["projects"][number];
export function ProjectFinish({
  project,
  act,
  busy,
}: {
  project: Project;
  act: (action: string, data?: unknown) => Promise<unknown>;
  busy: boolean;
}) {
  const [open, setOpen] = useState(false);
  const [outcome, setOutcome] = useState(project.outcome);
  const [step, setStep] = useState(project.nextStep);
  const [finish, setFinish] = useState(project.doneWhen || "");
  const [minutes, setMinutes] = useState(25);
  const [proof, setProof] = useState(project.proof || "");
  const [verified, setVerified] = useState(false);
  return (
    <section className="card project-card">
      <div className="section-heading">
        <h2>{project.title}</h2>
        <span className="tag">
          {project.stage === "delivered"
            ? "Delivered"
            : project.stage === "active"
              ? "One milestone chosen"
              : "To assess"}
        </span>
      </div>
      <p>{project.outcome}</p>
      <p className="muted">{project.nextStep}</p>
      {project.doneWhen && (
        <div className="definition">
          <strong>Finish line</strong>
          <p>{project.doneWhen}</p>
        </div>
      )}
      <small className="source">{project.source}</small>
      {project.stage === "delivered" && (
        <p>
          <Check size={16} /> {project.proof}
        </p>
      )}
      <button className="small-button" onClick={() => setOpen(!open)}>
        {open ? "Close review" : "Choose or review the next milestone"}{" "}
        <ArrowRight size={16} />
      </button>
      {open && (
        <div className="draft-fields">
          <label>
            What useful result will this deliver?
            <textarea
              maxLength={1000}
              value={outcome}
              onChange={(e) => setOutcome(e.target.value)}
            />
          </label>
          <label>
            The next small step
            <textarea
              maxLength={500}
              value={step}
              onChange={(e) => setStep(e.target.value)}
            />
          </label>
          <label>
            How will you know this milestone is finished?
            <textarea
              maxLength={500}
              value={finish}
              onChange={(e) => setFinish(e.target.value)}
              placeholder="A result someone can actually use or review"
            />
          </label>
          <label>
            Minutes for the next step
            <input
              type="number"
              min={5}
              max={480}
              value={minutes}
              onChange={(e) => setMinutes(Number(e.target.value))}
            />
          </label>
          <button
            className="small-button"
            disabled={busy || !outcome.trim() || !step.trim() || !finish.trim()}
            onClick={() =>
              act("commitProject", {
                id: project.id,
                outcome,
                nextStep: step,
                doneWhen: finish,
                minutes,
              })
            }
          >
            Use this milestone in my plan
          </button>
          {project.stage === "active" && (
            <details>
              <summary>Record that the project delivered</summary>
              <label>
                What did you check, and where is the usable result?
                <textarea
                  maxLength={1000}
                  value={proof}
                  onChange={(e) => setProof(e.target.value)}
                />
              </label>
              <label className="toggle-row">
                <input
                  type="checkbox"
                  checked={verified}
                  onChange={(e) => setVerified(e.target.checked)}
                />{" "}
                I checked the result against the finish line.
              </label>
              <button
                className="small-button"
                disabled={busy || !verified || proof.trim().length < 10}
                onClick={() =>
                  act("finishProject", { id: project.id, proof, verified })
                }
              >
                Record delivery
              </button>
              <p className="muted">
                Review unfinished project steps first. A commit or passing test
                alone is not delivery.
              </p>
            </details>
          )}
        </div>
      )}
    </section>
  );
}
