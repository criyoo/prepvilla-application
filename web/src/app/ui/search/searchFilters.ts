import {
  ALL_TUTOR_SUBJECT_OPTIONS,
  SUBJECT_CATEGORIES,
  WORLD_LANGUAGES,
  findSubjectCategoryByKey,
  findSubjectCategoryByLabel,
  findSubjectCategoryBySubject,
  subjectTermsMatch,
} from "../shared/nigeriaData";

export type TutorSearchFilters = {
  subjectCategory: string;
  subject: string;
  state: string;
  location: string;
  minRate: string;
  maxRate: string;
  qualification: string;
  gender: string;
  language: string;
};

export const EMPTY_TUTOR_SEARCH_FILTERS: TutorSearchFilters = {
  subjectCategory: "",
  subject: "",
  state: "",
  location: "",
  minRate: "",
  maxRate: "",
  qualification: "",
  gender: "",
  language: "",
};

export const QUALIFICATION_OPTIONS = [
  { value: "", label: "Any qualification" },
  { value: "NCE", label: "NCE" },
  { value: "BEd", label: "BEd" },
  { value: "PGDE", label: "PGDE" },
  { value: "MEd", label: "MEd" },
  { value: "OND", label: "OND" },
  { value: "HND", label: "HND" },
  { value: "BSc", label: "BSc" },
  { value: "MSc", label: "MSc" },
  { value: "MBA", label: "MBA" },
  { value: "Phd", label: "Phd" },
];

export const GENDER_OPTIONS = [
  { value: "", label: "Any gender" },
  { value: "male", label: "Male" },
  { value: "female", label: "Female" },
];

export const SUBJECT_CATEGORY_OPTIONS = [
  { value: "", label: "All categories" },
  ...SUBJECT_CATEGORIES.map((category) => ({ value: category.key, label: category.label })),
];

export const SUBJECT_OPTIONS = [
  { value: "", label: "All subjects" },
  ...ALL_TUTOR_SUBJECT_OPTIONS.map((subject) => ({ value: subject, label: subject })),
];

export const LANGUAGE_OPTIONS = [
  { value: "", label: "Any language" },
  ...WORLD_LANGUAGES.map((language) => ({ value: language, label: language })),
];

function readParam(params: { get(name: string): string | null }, name: string) {
  return params.get(name)?.trim() ?? "";
}

function deriveSubjectState(subjectCategoryParam: string, subjectParam: string) {
  const categoryByKey = findSubjectCategoryByKey(subjectCategoryParam);
  const categoryByLabel = findSubjectCategoryByLabel(subjectCategoryParam);
  const matchedCategory = categoryByKey ?? categoryByLabel;
  const matchedSubjectCategory = findSubjectCategoryBySubject(subjectParam);

  const normalizedCategory =
    matchedSubjectCategory?.key ??
    matchedCategory?.key ??
    "";

  const normalizedSubject = subjectTermsMatch(subjectParam, matchedCategory?.label ?? "")
    ? ""
    : subjectParam;

  return {
    subjectCategory: normalizedCategory,
    subject: normalizedSubject,
  };
}

export function parseTutorSearchParams(params: { get(name: string): string | null }): TutorSearchFilters {
  const legacyQuery = readParam(params, "query") || readParam(params, "q");
  const rawSubjectCategory = readParam(params, "subjectCategory");
  const rawSubject = readParam(params, "subject") || legacyQuery;
  const { subjectCategory, subject } = deriveSubjectState(rawSubjectCategory || legacyQuery, rawSubject);

  return {
    subjectCategory,
    subject,
    state: readParam(params, "state"),
    location: readParam(params, "location"),
    minRate: readParam(params, "minRate"),
    maxRate: readParam(params, "maxRate"),
    qualification: readParam(params, "qualification"),
    gender: readParam(params, "gender"),
    language: readParam(params, "language"),
  };
}

export function buildTutorSearchParams(filters: TutorSearchFilters) {
  const params = new URLSearchParams();
  if (filters.subjectCategory.trim()) params.set("subjectCategory", filters.subjectCategory.trim());
  if (filters.subject.trim()) params.set("subject", filters.subject.trim());
  if (filters.state.trim()) params.set("state", filters.state.trim());
  if (filters.location.trim()) params.set("location", filters.location.trim());
  if (filters.minRate.trim()) params.set("minRate", filters.minRate.trim());
  if (filters.maxRate.trim()) params.set("maxRate", filters.maxRate.trim());
  if (filters.qualification.trim()) params.set("qualification", filters.qualification.trim());
  if (filters.gender.trim()) params.set("gender", filters.gender.trim());
  if (filters.language.trim()) params.set("language", filters.language.trim());
  return params;
}

export function buildTutorApiSearchParams(filters: TutorSearchFilters) {
  const params = new URLSearchParams();
  if (filters.subject.trim()) params.set("q", filters.subject.trim());
  if (filters.state.trim()) params.set("state", filters.state.trim());
  if (filters.location.trim()) params.set("location", filters.location.trim());
  if (filters.minRate.trim()) params.set("minRate", filters.minRate.trim());
  if (filters.maxRate.trim()) params.set("maxRate", filters.maxRate.trim());
  if (filters.qualification.trim()) params.set("qualification", filters.qualification.trim());
  if (filters.gender.trim()) params.set("gender", filters.gender.trim());
  if (filters.language.trim()) params.set("language", filters.language.trim());
  return params;
}
