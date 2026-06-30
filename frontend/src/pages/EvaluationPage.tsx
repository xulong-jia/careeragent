import { useEffect, useState } from "react";

import {
  getEvaluationRun,
  getEvaluationStats,
  listEvaluationDatasets,
  listEvaluationCases,
  listEvaluationResults,
  listEvaluationRuns,
  runEvaluation,
} from "../api/evaluations";
import type {
  EvaluationCaseRecord,
  EvaluationDatasetRecord,
  EvaluationModule,
  EvaluationResultRecord,
  EvaluationRunModule,
  EvaluationRunRecord,
  EvaluationRunSummary,
  EvaluationStats,
} from "../types/api";

const moduleOptions: EvaluationRunModule[] = [
  "all",
  "jd_parser",
  "resume_parser",
  "match",
  "rag",
  "agent",
  "application",
  "bad_case",
];

function formatDate(value: string | null) {
  return value ? new Date(value).toLocaleString() : "None";
}

function statusClass(status: string) {
  return `status-pill status-${status.replace(/_/g, "-")}`;
}

function metricNumber(
  metrics: Record<string, unknown>,
  key: "total_count" | "passed_count" | "failed_count" | "pass_rate",
) {
  const value = metrics[key];
  return typeof value === "number" ? value : 0;
}

function moduleCaseCount(
  byModule: Record<EvaluationModule, number> | undefined,
  module: EvaluationModule,
) {
  return byModule?.[module] ?? 0;
}

export function EvaluationPage() {
  const [stats, setStats] = useState<EvaluationStats | null>(null);
  const [runs, setRuns] = useState<EvaluationRunRecord[]>([]);
  const [cases, setCases] = useState<EvaluationCaseRecord[]>([]);
  const [datasets, setDatasets] = useState<EvaluationDatasetRecord[]>([]);
  const [results, setResults] = useState<EvaluationResultRecord[]>([]);
  const [selectedResult, setSelectedResult] =
    useState<EvaluationResultRecord | null>(null);
  const [selectedRun, setSelectedRun] = useState<EvaluationRunSummary | null>(
    null,
  );
  const [selectedModule, setSelectedModule] =
    useState<EvaluationRunModule>("all");
  const [isLoading, setIsLoading] = useState(false);
  const [isRunning, setIsRunning] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  const refreshStats = async () => {
    const nextStats = await getEvaluationStats();
    setStats(nextStats);
    return nextStats;
  };

  const loadRun = async (runId: string) => {
    const [summary, resultList] = await Promise.all([
      getEvaluationRun(runId),
      listEvaluationResults(runId),
    ]);
    setSelectedRun(summary);
    setResults(resultList.items);
    setSelectedResult(
      resultList.items.find((result) => !result.passed) ??
        resultList.items[0] ??
        null,
    );
  };

  const refreshEvaluationData = async (nextRunId?: string) => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const [runList, caseList, datasetList] = await Promise.all([
        listEvaluationRuns({ limit: 50 }),
        listEvaluationCases({ limit: 100 }),
        listEvaluationDatasets(),
        refreshStats(),
      ]);
      setRuns(runList.items);
      setCases(caseList.items);
      setDatasets(datasetList.items);
      const runId = nextRunId ?? runList.items[0]?.id ?? null;
      if (runId) {
        await loadRun(runId);
      } else {
        setSelectedRun(null);
        setResults([]);
        setSelectedResult(null);
      }
    } catch (error) {
      setErrorMessage(
        error instanceof Error ? error.message : "Evaluation 数据加载失败。",
      );
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    void refreshEvaluationData();
  }, []);

  const handleRunEvaluation = async () => {
    setIsRunning(true);
    setErrorMessage(null);
    setStatusMessage(null);
    try {
      const summary = await runEvaluation({
        module: selectedModule,
        dataset_name: "synthetic_smoke_v1",
        name: `Synthetic smoke ${selectedModule}`,
      });
      setSelectedRun(summary);
      setStatusMessage("Evaluation run completed.");
      await refreshEvaluationData(summary.run.id);
    } catch (error) {
      setErrorMessage(
        error instanceof Error ? error.message : "Evaluation run 创建失败。",
      );
    } finally {
      setIsRunning(false);
    }
  };

  const handleSelectRun = async (runId: string) => {
    setIsLoading(true);
    setErrorMessage(null);
    setStatusMessage(null);
    try {
      await loadRun(runId);
    } catch (error) {
      setErrorMessage(
        error instanceof Error ? error.message : "Evaluation run 加载失败。",
      );
    } finally {
      setIsLoading(false);
    }
  };

  const selectedMetrics = selectedRun?.run.metrics ?? {};
  const failedResults = results.filter((result) => !result.passed);

  return (
    <section className="page-stack" aria-labelledby="evaluation-title">
      <div className="page-heading">
        <p className="eyebrow">Evaluation</p>
        <h2 id="evaluation-title">Evaluation Center</h2>
        <p>Deterministic smoke set、runs、cases 和 results。</p>
      </div>

      {errorMessage ? <p className="error-text">{errorMessage}</p> : null}
      {statusMessage ? <p className="hint-text">{statusMessage}</p> : null}

      <div className="metric-grid">
        <article className="metric-card blue">
          <span>Runs</span>
          <strong>{stats?.total_runs ?? 0}</strong>
          <small>{stats?.latest_run_status ?? "No runs"}</small>
        </article>
        <article className="metric-card green">
          <span>Pass Rate</span>
          <strong>
            {stats?.latest_pass_rate != null
              ? `${Math.round(stats.latest_pass_rate * 100)}%`
              : "0%"}
          </strong>
          <small>Latest run</small>
        </article>
        <article className="metric-card amber">
          <span>Cases</span>
          <strong>{stats?.total_cases ?? 0}</strong>
          <small>Synthetic / manual / bad case</small>
        </article>
        <article className="metric-card red">
          <span>Failed</span>
          <strong>{stats?.failed_results ?? 0}</strong>
          <small>Stored results</small>
        </article>
      </div>

      <article className="panel">
        <div className="panel-header">
          <div>
            <h3>Synthetic Smoke Evaluation</h3>
            <p className="helper-text">deterministic runner / no LLM judge</p>
          </div>
          <span className="status-pill muted">synthetic_smoke_v1</span>
        </div>
        <div className="inline-form">
          <select
            aria-label="Evaluation module"
            onChange={(event) =>
              setSelectedModule(event.target.value as EvaluationRunModule)
            }
            value={selectedModule}
          >
            {moduleOptions.map((module) => (
              <option key={module} value={module}>
                {module}
              </option>
            ))}
          </select>
          <button
            className="primary-action"
            disabled={isRunning}
            onClick={handleRunEvaluation}
            type="button"
          >
            {isRunning ? "Running..." : "Run smoke set"}
          </button>
          <button
            className="ghost-action"
            disabled={isLoading}
            onClick={() => void refreshEvaluationData()}
            type="button"
          >
            Refresh
          </button>
        </div>
      </article>

      <article className="panel">
        <div className="panel-header">
          <h3>Datasets</h3>
          <span className="status-pill muted">{datasets.length} registered</span>
        </div>
        {datasets.length ? (
          <ul className="activity-list evaluation-case-list">
            {datasets.map((dataset) => (
              <li
                key={`${dataset.dataset_name}-${dataset.module}-${dataset.source_type}`}
              >
                <div>
                  <strong>{dataset.dataset_name}</strong>
                  <small>{dataset.description}</small>
                </div>
                <span>{dataset.module}</span>
                <span>{dataset.case_count} cases</span>
                <span className={statusClass(dataset.source_type)}>
                  {dataset.source_type}
                </span>
                <span>{dataset.version ?? "None"}</span>
              </li>
            ))}
          </ul>
        ) : (
          <div className="empty-state compact">
            <strong>No datasets</strong>
            <span>Refresh to load dataset metadata.</span>
          </div>
        )}
      </article>

      <div className="two-column wide-left">
        <article className="panel">
          <div className="panel-header">
            <h3>Runs</h3>
            <span className="status-pill muted">{runs.length} records</span>
          </div>
          {runs.length ? (
            <ul className="activity-list evaluation-run-list">
              {runs.map((run) => (
                <li
                  className={
                    selectedRun?.run.id === run.id ? "selected-row" : undefined
                  }
                  key={run.id}
                >
                  <div>
                    <strong>{run.name}</strong>
                    <small>{run.id}</small>
                  </div>
                  <span>{run.module}</span>
                  <span>{run.dataset_name}</span>
                  <span className={statusClass(run.status)}>{run.status}</span>
                  <button
                    className="ghost-action"
                    onClick={() => void handleSelectRun(run.id)}
                    type="button"
                  >
                    View
                  </button>
                </li>
              ))}
            </ul>
          ) : (
            <div className="empty-state compact">
              <strong>No evaluation runs</strong>
              <span>Run synthetic smoke set first.</span>
            </div>
          )}
        </article>

        <article className="panel">
          <div className="panel-header">
            <h3>Latest Metrics</h3>
            <span className="status-pill muted">
              {selectedRun?.run.id ?? "None"}
            </span>
          </div>
          {selectedRun ? (
            <>
              <ul className="activity-list">
                <li>
                  <strong>Total</strong>
                  <span>{metricNumber(selectedMetrics, "total_count")}</span>
                </li>
                <li>
                  <strong>Passed</strong>
                  <span>{metricNumber(selectedMetrics, "passed_count")}</span>
                </li>
                <li>
                  <strong>Failed</strong>
                  <span>{metricNumber(selectedMetrics, "failed_count")}</span>
                </li>
                <li>
                  <strong>Pass Rate</strong>
                  <span>
                    {Math.round(metricNumber(selectedMetrics, "pass_rate") * 100)}%
                  </span>
                </li>
                <li>
                  <strong>Finished</strong>
                  <span>{formatDate(selectedRun.run.finished_at)}</span>
                </li>
              </ul>
              <pre className="json-preview compact">
                {JSON.stringify(selectedRun.run.metrics, null, 2)}
              </pre>
              <pre className="json-preview compact">
                {JSON.stringify(selectedRun.run.run_config, null, 2)}
              </pre>
            </>
          ) : (
            <div className="empty-state compact">
              <strong>No metrics</strong>
              <span>No run selected.</span>
            </div>
          )}
        </article>
      </div>

      <article className="panel">
        <div className="panel-header">
          <h3>Results</h3>
          <span className="status-pill muted">{results.length} rows</span>
        </div>
        {results.length ? (
          <ul className="activity-list evaluation-result-list">
            {results.map((result) => {
              const evaluationCase = cases.find(
                (item) => item.id === result.case_id,
              );
              return (
                <li key={result.id}>
                  <span>{result.module}</span>
                  <div>
                    <strong>{evaluationCase?.case_name ?? result.case_id}</strong>
                    <small>{result.id}</small>
                  </div>
                  <span className={statusClass(result.status)}>{result.status}</span>
                  <span>{result.score.toFixed(2)}</span>
                  <span>{result.error ?? "None"}</span>
                  <button
                    className="ghost-action"
                    onClick={() => setSelectedResult(result)}
                    type="button"
                  >
                    Detail
                  </button>
                </li>
              );
            })}
          </ul>
        ) : (
          <div className="empty-state compact">
            <strong>No results</strong>
            <span>No run selected.</span>
          </div>
        )}
      </article>

      <div className="two-column wide-left">
        <article className="panel">
          <div className="panel-header">
            <h3>Failed Cases</h3>
            <span className="status-pill muted">{failedResults.length} rows</span>
          </div>
          {failedResults.length ? (
            <ul className="activity-list">
              {failedResults.map((result) => (
                <li key={result.id}>
                  <div>
                    <strong>{result.case_id}</strong>
                    <small>{result.error ?? "No error"}</small>
                  </div>
                  <span>{result.module}</span>
                  <button
                    className="ghost-action"
                    onClick={() => setSelectedResult(result)}
                    type="button"
                  >
                    Detail
                  </button>
                </li>
              ))}
            </ul>
          ) : (
            <div className="empty-state compact">
              <strong>No failed cases</strong>
              <span>Selected run has no failing results.</span>
            </div>
          )}
        </article>

        <article className="panel">
          <div className="panel-header">
            <h3>Result Detail</h3>
            <span className="status-pill muted">
              {selectedResult?.id ?? "None"}
            </span>
          </div>
          {selectedResult ? (
            <>
              <ul className="activity-list">
                <li>
                  <strong>Case</strong>
                  <span>{selectedResult.case_id}</span>
                </li>
                <li>
                  <strong>Status</strong>
                  <span className={statusClass(selectedResult.status)}>
                    {selectedResult.status}
                  </span>
                </li>
                <li>
                  <strong>Error</strong>
                  <span>{selectedResult.error ?? "None"}</span>
                </li>
              </ul>
              <pre className="json-preview compact">
                {JSON.stringify(
                  {
                    actual_output: selectedResult.actual_output,
                    expected_output: selectedResult.expected_output,
                  },
                  null,
                  2,
                )}
              </pre>
            </>
          ) : (
            <div className="empty-state compact">
              <strong>No result selected</strong>
              <span>Select a result row for detail.</span>
            </div>
          )}
        </article>
      </div>

      <article className="panel">
        <div className="panel-header">
          <h3>Cases</h3>
          <span className="status-pill muted">
            jd {moduleCaseCount(stats?.by_module, "jd_parser")} / resume{" "}
            {moduleCaseCount(stats?.by_module, "resume_parser")} / match{" "}
            {moduleCaseCount(stats?.by_module, "match")} / rag{" "}
            {moduleCaseCount(stats?.by_module, "rag")} / agent{" "}
            {moduleCaseCount(stats?.by_module, "agent")}
          </span>
        </div>
        {cases.length ? (
          <ul className="activity-list evaluation-case-list">
            {cases.map((evaluationCase) => (
              <li key={evaluationCase.id}>
                <div>
                  <strong>{evaluationCase.case_name}</strong>
                  <small>{evaluationCase.id}</small>
                </div>
                <span>{evaluationCase.module}</span>
                <span>{evaluationCase.dataset_name}</span>
                <span className={statusClass(evaluationCase.source_type)}>
                  {evaluationCase.source_type}
                </span>
              </li>
            ))}
          </ul>
        ) : (
          <div className="empty-state compact">
            <strong>No cases</strong>
            <span>Run synthetic smoke set to seed cases.</span>
          </div>
        )}
      </article>
    </section>
  );
}
