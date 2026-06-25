import { useEffect, useState } from "react";

import {
  generateInterviewQuestions,
  listInterviewAnswers,
  listInterviewQuestions,
  scoreInterviewAnswer,
  submitInterviewAnswer,
} from "../api/interviews";
import type {
  InterviewAnswerRecord,
  InterviewDifficulty,
  InterviewQuestionRecord,
  InterviewQuestionType,
  InterviewScores,
  InterviewSourceRef,
} from "../types/api";

type GenerateFormState = {
  jdId: string;
  resumeVersionId: string;
  projectId: string;
  projectRewriteId: string;
  ragAnswerRunIds: string;
  questionTypes: string;
  maxQuestions: string;
};

type QuestionFiltersState = {
  jdId: string;
  resumeVersionId: string;
  projectId: string;
  questionType: InterviewQuestionType | "";
  difficulty: InterviewDifficulty | "";
};

const questionTypeOptions: InterviewQuestionType[] = [
  "project_deep_dive",
  "technical_depth",
  "jd_skill_check",
  "risk_or_gap_explanation",
  "behavior_or_collaboration",
  "resume_challenge",
];

const difficultyOptions: InterviewDifficulty[] = ["easy", "medium", "hard"];

const scoreLabels: Array<[keyof InterviewScores, string]> = [
  ["structure", "Structure"],
  ["technical_depth", "Technical Depth"],
  ["business_understanding", "Business Understanding"],
  ["evidence", "Evidence"],
  ["clarity", "Clarity"],
  ["risk_control", "Risk Control"],
  ["overall_average", "Overall Average"],
];

function initialGenerateForm(): GenerateFormState {
  return {
    jdId: "",
    resumeVersionId: "",
    projectId: "",
    projectRewriteId: "",
    ragAnswerRunIds: "",
    questionTypes: "",
    maxQuestions: "6",
  };
}

function initialQuestionFilters(): QuestionFiltersState {
  return {
    jdId: "",
    resumeVersionId: "",
    projectId: "",
    questionType: "",
    difficulty: "",
  };
}

function optionalText(value: string): string | null {
  const normalized = value.trim();
  return normalized || null;
}

function parseCsv(value: string): string[] {
  return value
    .split(/[\n,]/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function parseQuestionTypes(value: string): InterviewQuestionType[] | null {
  const items = value
    .split(/[\n,]/)
    .map((item) => item.trim())
    .filter(Boolean);
  if (items.length === 0) {
    return null;
  }
  const invalid = items.find(
    (item): item is string =>
      !questionTypeOptions.includes(item as InterviewQuestionType),
  );
  if (invalid) {
    throw new Error(`Unsupported question type: ${invalid}`);
  }
  return items as InterviewQuestionType[];
}

function parseMaxQuestions(value: string): number {
  const normalized = value.trim();
  if (!normalized) {
    return 6;
  }
  const parsed = Number(normalized);
  if (!Number.isInteger(parsed) || parsed < 1 || parsed > 12) {
    throw new Error("Max questions must be an integer from 1 to 12.");
  }
  return parsed;
}

function formatDate(value: string): string {
  return new Date(value).toLocaleString();
}

function renderPoint(point: Record<string, unknown>, index: number): string {
  const label =
    typeof point.label === "string"
      ? point.label
      : typeof point.point === "string"
        ? point.point
        : typeof point.description === "string"
          ? point.description
          : null;
  return label ?? `Expected point ${index + 1}`;
}

function SourceRefList({ refs }: { refs: InterviewSourceRef[] }) {
  if (refs.length === 0) {
    return <span className="muted-inline">No source refs</span>;
  }
  return (
    <ul className="compact-list source-ref-list">
      {refs.map((ref) => (
        <li key={`${ref.source_type}-${ref.source_id}-${ref.field}-${ref.preview}`}>
          <strong>{ref.label}</strong>
          <span>
            {ref.source_type}/{ref.field}: {ref.preview}
          </span>
        </li>
      ))}
    </ul>
  );
}

function ScoreGrid({ scores }: { scores: InterviewScores }) {
  return (
    <div className="interview-score-grid">
      {scoreLabels.map(([key, label]) => (
        <div
          className={key === "risk_control" ? "score-chip warning" : "score-chip"}
          key={key}
        >
          <span>{label}</span>
          <strong>{scores[key] ?? "--"}</strong>
        </div>
      ))}
    </div>
  );
}

export function InterviewCenterPage() {
  const [generateForm, setGenerateForm] =
    useState<GenerateFormState>(initialGenerateForm);
  const [questionFilters, setQuestionFilters] =
    useState<QuestionFiltersState>(initialQuestionFilters);
  const [questions, setQuestions] = useState<InterviewQuestionRecord[]>([]);
  const [answers, setAnswers] = useState<InterviewAnswerRecord[]>([]);
  const [selectedQuestion, setSelectedQuestion] =
    useState<InterviewQuestionRecord | null>(null);
  const [selectedAnswer, setSelectedAnswer] =
    useState<InterviewAnswerRecord | null>(null);
  const [answerText, setAnswerText] = useState("");
  const [warnings, setWarnings] = useState<string[]>([]);
  const [needMoreInfo, setNeedMoreInfo] = useState<string[]>([]);
  const [questionLoading, setQuestionLoading] = useState(false);
  const [answerLoading, setAnswerLoading] = useState(false);
  const [scoreLoading, setScoreLoading] = useState(false);
  const [pageError, setPageError] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  const generateValidationError =
    !generateForm.jdId.trim() || !generateForm.resumeVersionId.trim()
      ? "JD ID and Resume Version ID are required."
      : null;
  const answerValidationError =
    selectedQuestion && !answerText.trim() ? "Answer text is required." : null;
  const canGenerate = !generateValidationError && !questionLoading;
  const canSubmitAnswer =
    Boolean(selectedQuestion) && Boolean(answerText.trim()) && !answerLoading;
  const canScore = Boolean(selectedAnswer) && !scoreLoading;

  const refreshQuestions = async () => {
    setQuestionLoading(true);
    setPageError(null);
    try {
      const response = await listInterviewQuestions({
        jd_id: optionalText(questionFilters.jdId) ?? undefined,
        resume_version_id: optionalText(questionFilters.resumeVersionId) ?? undefined,
        project_id: optionalText(questionFilters.projectId) ?? undefined,
        question_type: questionFilters.questionType,
        difficulty: questionFilters.difficulty,
      });
      setQuestions(response.items);
      setSelectedQuestion((current) =>
        current
          ? response.items.find((item) => item.id === current.id) ?? null
          : response.items[0] ?? null,
      );
    } catch (error) {
      setPageError(
        error instanceof Error ? error.message : "Question list load failed.",
      );
    } finally {
      setQuestionLoading(false);
    }
  };

  const refreshAnswers = async (questionId?: string) => {
    setAnswerLoading(true);
    setPageError(null);
    try {
      const response = await listInterviewAnswers({
        question_id: questionId || selectedQuestion?.id,
      });
      setAnswers(response.items);
      setSelectedAnswer((current) =>
        current
          ? response.items.find((item) => item.id === current.id) ?? null
          : response.items[0] ?? null,
      );
    } catch (error) {
      setPageError(
        error instanceof Error ? error.message : "Answer list load failed.",
      );
    } finally {
      setAnswerLoading(false);
    }
  };

  useEffect(() => {
    void refreshQuestions();
  }, []);

  useEffect(() => {
    if (selectedQuestion) {
      void refreshAnswers(selectedQuestion.id);
    } else {
      setAnswers([]);
      setSelectedAnswer(null);
    }
  }, [selectedQuestion?.id]);

  const handleGenerateQuestions = async () => {
    if (generateValidationError) {
      setPageError(generateValidationError);
      return;
    }
    setQuestionLoading(true);
    setPageError(null);
    setStatusMessage(null);
    try {
      const result = await generateInterviewQuestions({
        jd_id: generateForm.jdId.trim(),
        resume_version_id: generateForm.resumeVersionId.trim(),
        project_id: optionalText(generateForm.projectId),
        project_rewrite_id: optionalText(generateForm.projectRewriteId),
        rag_answer_run_ids: parseCsv(generateForm.ragAnswerRunIds),
        question_types: parseQuestionTypes(generateForm.questionTypes),
        max_questions: parseMaxQuestions(generateForm.maxQuestions),
      });
      setWarnings(result.warnings);
      setNeedMoreInfo(result.need_more_info);
      setQuestions(result.questions);
      setSelectedQuestion(result.questions[0] ?? null);
      setSelectedAnswer(null);
      setStatusMessage(`Generated ${result.questions.length} questions.`);
    } catch (error) {
      setPageError(
        error instanceof Error ? error.message : "Question generation failed.",
      );
    } finally {
      setQuestionLoading(false);
    }
  };

  const handleSelectQuestion = (question: InterviewQuestionRecord) => {
    setSelectedQuestion(question);
    setSelectedAnswer(null);
    setAnswerText("");
    setPageError(null);
    setStatusMessage(null);
  };

  const handleSubmitAnswer = async () => {
    if (!selectedQuestion) {
      setPageError("Select a question before submitting an answer.");
      return;
    }
    if (!answerText.trim()) {
      setPageError("Answer text is required.");
      return;
    }
    setAnswerLoading(true);
    setPageError(null);
    setStatusMessage(null);
    try {
      const answer = await submitInterviewAnswer({
        question_id: selectedQuestion.id,
        answer_text: answerText.trim(),
      });
      setSelectedAnswer(answer);
      setAnswers((current) => [answer, ...current.filter((item) => item.id !== answer.id)]);
      setAnswerText("");
      setStatusMessage("Answer submitted. Only preview is shown after save.");
    } catch (error) {
      setPageError(
        error instanceof Error ? error.message : "Answer submit failed.",
      );
    } finally {
      setAnswerLoading(false);
    }
  };

  const handleScoreAnswer = async () => {
    if (!selectedAnswer) {
      setPageError("Select an answer before scoring.");
      return;
    }
    setScoreLoading(true);
    setPageError(null);
    setStatusMessage(null);
    try {
      const scored = await scoreInterviewAnswer(selectedAnswer.id);
      setSelectedAnswer(scored);
      setAnswers((current) =>
        current.map((item) => (item.id === scored.id ? scored : item)),
      );
      setStatusMessage("Answer scored with deterministic rules.");
    } catch (error) {
      setPageError(error instanceof Error ? error.message : "Scoring failed.");
    } finally {
      setScoreLoading(false);
    }
  };

  return (
    <section className="page-stack" aria-labelledby="interview-center-title">
      <div className="page-heading">
        <p className="eyebrow">Interview Center</p>
        <h2 id="interview-center-title">Interview Center</h2>
        <p>Question generation, answer submit and deterministic scoring for synthetic interview practice.</p>
      </div>

      <article className="panel warning-panel">
        <div>
          <h3>Privacy Boundary</h3>
          <p>Saved answers are displayed as previews only. Resume and JD full raw text are not rendered on this page.</p>
        </div>
        <span className="status-pill">No LLM judge</span>
      </article>

      {pageError ? <p className="error-text">{pageError}</p> : null}
      {generateValidationError ? (
        <p className="error-text">{generateValidationError}</p>
      ) : null}
      {answerValidationError ? (
        <p className="error-text">{answerValidationError}</p>
      ) : null}
      {statusMessage ? <p className="hint-text">{statusMessage}</p> : null}

      <div className="two-column wide-left">
        <article className="panel">
          <div className="panel-header">
            <h3>Generate Questions</h3>
            <span className="status-pill muted">POST /api/interviews/questions/generate</span>
          </div>
          <div className="form-stack">
            <div className="filter-grid">
              <label>
                JD ID required
                <input
                  onChange={(event) =>
                    setGenerateForm((current) => ({
                      ...current,
                      jdId: event.target.value,
                    }))
                  }
                  value={generateForm.jdId}
                />
              </label>
              <label>
                Resume Version ID required
                <input
                  onChange={(event) =>
                    setGenerateForm((current) => ({
                      ...current,
                      resumeVersionId: event.target.value,
                    }))
                  }
                  value={generateForm.resumeVersionId}
                />
              </label>
              <label>
                Project ID optional
                <input
                  onChange={(event) =>
                    setGenerateForm((current) => ({
                      ...current,
                      projectId: event.target.value,
                    }))
                  }
                  value={generateForm.projectId}
                />
              </label>
              <label>
                Project Rewrite ID optional
                <input
                  onChange={(event) =>
                    setGenerateForm((current) => ({
                      ...current,
                      projectRewriteId: event.target.value,
                    }))
                  }
                  value={generateForm.projectRewriteId}
                />
              </label>
              <label>
                RAG Answer Run IDs optional
                <input
                  onChange={(event) =>
                    setGenerateForm((current) => ({
                      ...current,
                      ragAnswerRunIds: event.target.value,
                    }))
                  }
                  placeholder="rag_answer_run_..."
                  value={generateForm.ragAnswerRunIds}
                />
              </label>
              <label>
                Question types optional
                <input
                  onChange={(event) =>
                    setGenerateForm((current) => ({
                      ...current,
                      questionTypes: event.target.value,
                    }))
                  }
                  placeholder="technical_depth, jd_skill_check"
                  value={generateForm.questionTypes}
                />
              </label>
              <label>
                Max questions optional
                <input
                  inputMode="numeric"
                  onChange={(event) =>
                    setGenerateForm((current) => ({
                      ...current,
                      maxQuestions: event.target.value,
                    }))
                  }
                  value={generateForm.maxQuestions}
                />
              </label>
            </div>
            <button
              className="primary-action"
              disabled={!canGenerate}
              onClick={handleGenerateQuestions}
              type="button"
            >
              {questionLoading ? "Generating..." : "Generate Questions"}
            </button>
          </div>
          {warnings.length || needMoreInfo.length ? (
            <div className="notice-grid">
              {warnings.length ? (
                <div className="notice-box warning">
                  <strong>Warnings</strong>
                  <ul className="compact-list">
                    {warnings.map((warning) => (
                      <li key={warning}>{warning}</li>
                    ))}
                  </ul>
                </div>
              ) : null}
              {needMoreInfo.length ? (
                <div className="notice-box">
                  <strong>Need more info</strong>
                  <ul className="compact-list">
                    {needMoreInfo.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                </div>
              ) : null}
            </div>
          ) : null}
        </article>

        <article className="panel">
          <div className="panel-header">
            <h3>Question Filters</h3>
            <button
              className="ghost-action"
              disabled={questionLoading}
              onClick={() => void refreshQuestions()}
              type="button"
            >
              {questionLoading ? "Loading..." : "Refresh"}
            </button>
          </div>
          <div className="form-stack">
            <div className="filter-grid single">
              <label>
                JD ID
                <input
                  onChange={(event) =>
                    setQuestionFilters((current) => ({
                      ...current,
                      jdId: event.target.value,
                    }))
                  }
                  value={questionFilters.jdId}
                />
              </label>
              <label>
                Resume Version ID
                <input
                  onChange={(event) =>
                    setQuestionFilters((current) => ({
                      ...current,
                      resumeVersionId: event.target.value,
                    }))
                  }
                  value={questionFilters.resumeVersionId}
                />
              </label>
              <label>
                Project ID
                <input
                  onChange={(event) =>
                    setQuestionFilters((current) => ({
                      ...current,
                      projectId: event.target.value,
                    }))
                  }
                  value={questionFilters.projectId}
                />
              </label>
              <label>
                Question type
                <select
                  onChange={(event) =>
                    setQuestionFilters((current) => ({
                      ...current,
                      questionType: event.target.value as InterviewQuestionType | "",
                    }))
                  }
                  value={questionFilters.questionType}
                >
                  <option value="">All</option>
                  {questionTypeOptions.map((type) => (
                    <option key={type} value={type}>
                      {type}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Difficulty
                <select
                  onChange={(event) =>
                    setQuestionFilters((current) => ({
                      ...current,
                      difficulty: event.target.value as InterviewDifficulty | "",
                    }))
                  }
                  value={questionFilters.difficulty}
                >
                  <option value="">All</option>
                  {difficultyOptions.map((difficulty) => (
                    <option key={difficulty} value={difficulty}>
                      {difficulty}
                    </option>
                  ))}
                </select>
              </label>
            </div>
          </div>
        </article>
      </div>

      <article className="panel">
        <div className="panel-header">
          <h3>Question List</h3>
          <span className="status-pill muted">{questions.length} records</span>
        </div>
        {questions.length === 0 ? (
          <div className="empty-state compact">
            <strong>No questions</strong>
            <span>Generate or refresh filtered questions.</span>
          </div>
        ) : (
          <ul className="activity-list interview-question-list">
            {questions.map((question) => (
              <li
                className={
                  selectedQuestion?.id === question.id ? "selected-row" : undefined
                }
                key={question.id}
              >
                <div>
                  <strong>{question.question}</strong>
                  <small>
                    {question.question_type} / {question.difficulty} / {formatDate(question.created_at)}
                  </small>
                  <ul className="compact-list">
                    {question.expected_points.map((point, index) => (
                      <li key={`${question.id}-point-${index}`}>
                        {renderPoint(point, index)}
                      </li>
                    ))}
                  </ul>
                  <SourceRefList refs={question.source_refs} />
                </div>
                <button
                  className="ghost-action"
                  onClick={() => handleSelectQuestion(question)}
                  type="button"
                >
                  Select
                </button>
              </li>
            ))}
          </ul>
        )}
      </article>

      <div className="two-column">
        <article className="panel">
          <div className="panel-header">
            <h3>Submit Answer</h3>
            <span className="status-pill muted">
              {selectedQuestion?.id ?? "No question"}
            </span>
          </div>
          <div className="form-stack">
            <label>
              Answer text
              <textarea
                className="metadata-textarea answer-textarea"
                onChange={(event) => setAnswerText(event.target.value)}
                value={answerText}
              />
            </label>
            <div className="inline-form">
              <button
                className="primary-action"
                disabled={!canSubmitAnswer}
                onClick={handleSubmitAnswer}
                type="button"
              >
                {answerLoading ? "Submitting..." : "Submit Answer"}
              </button>
              <button
                className="ghost-action"
                disabled={!selectedQuestion || answerLoading}
                onClick={() => void refreshAnswers()}
                type="button"
              >
                {answerLoading ? "Loading..." : "Refresh Answers"}
              </button>
            </div>
          </div>
        </article>

        <article className="panel">
          <div className="panel-header">
            <h3>Score Answer</h3>
            <span className="status-pill muted">
              {selectedAnswer?.id ?? "No answer"}
            </span>
          </div>
          {selectedAnswer ? (
            <div className="score-result">
              <ScoreGrid scores={selectedAnswer.scores} />
              {selectedAnswer.feedback ? (
                <p className="feedback-text">{selectedAnswer.feedback}</p>
              ) : (
                <p className="hint-text">No score yet.</p>
              )}
              <div className="tag-row">
                {selectedAnswer.weakness_tags.length ? (
                  selectedAnswer.weakness_tags.map((tag) => (
                    <span className="status-pill status-need-more-info" key={tag}>
                      {tag}
                    </span>
                  ))
                ) : (
                  <span className="status-pill muted">No weakness tags</span>
                )}
              </div>
            </div>
          ) : (
            <div className="empty-state compact">
              <strong>No answer selected</strong>
              <span>Select or submit an answer before scoring.</span>
            </div>
          )}
          <button
            className="primary-action"
            disabled={!canScore}
            onClick={handleScoreAnswer}
            type="button"
          >
            {scoreLoading ? "Scoring..." : "Score Answer"}
          </button>
        </article>
      </div>

      <article className="panel">
        <div className="panel-header">
          <h3>Answer List</h3>
          <span className="status-pill muted">{answers.length} records</span>
        </div>
        {answers.length === 0 ? (
          <div className="empty-state compact">
            <strong>No answers</strong>
            <span>Submit an answer for the selected question.</span>
          </div>
        ) : (
          <ul className="activity-list answer-list">
            {answers.map((answer) => (
              <li
                className={selectedAnswer?.id === answer.id ? "selected-row" : undefined}
                key={answer.id}
              >
                <div>
                  <strong>{answer.id}</strong>
                  <small>Question: {answer.question_id}</small>
                  <span className="text-preview">{answer.answer_text_preview}</span>
                  <div className="tag-row">
                    {answer.weakness_tags.map((tag) => (
                      <span className="status-pill status-need-more-info" key={tag}>
                        {tag}
                      </span>
                    ))}
                  </div>
                </div>
                <span>overall {answer.scores.overall_average ?? "--"}</span>
                <span>{formatDate(answer.created_at)}</span>
                <button
                  className="ghost-action"
                  onClick={() => setSelectedAnswer(answer)}
                  type="button"
                >
                  Select
                </button>
              </li>
            ))}
          </ul>
        )}
      </article>
    </section>
  );
}
