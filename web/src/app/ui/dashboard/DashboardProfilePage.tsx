"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Image from "next/image";
import { useRouter, useSearchParams } from "next/navigation";
import { Button } from "../shared/Button";
import { Input } from "../shared/Input";
import { Select } from "../shared/Select";
import { Textarea } from "../shared/Textarea";
import { api } from "../shared/api";
import { useAuthStore } from "../shared/authStore";
import { useFormDraft } from "../shared/useFormDraft";
import { NIGERIAN_SCHOOL_SUBJECTS, NIGERIA_STATE_CITIES, NIGERIA_STATES, WORLD_LANGUAGES } from "../shared/nigeriaData";
import { getBvnNumberError, getNinNumberError, sanitizeMobileNumberInput, sanitizeNinInput, sanitizeBvnInput } from "../shared/profileValidation";
import type { UserRole } from "@prepvilla/types";

type MeResponse = {
  id: string;
  email: string;
  role: UserRole;
  displayName: string;
  timezone: string;
  fullName: string;
  firstName?: string;
  middleName?: string;
  lastName?: string;
  mobileNumber: string;
  dateOfBirth: string | null;
  gender?: string;
  isStudentProfileComplete?: boolean;
  levelOfEducation?: string;
  profilePhotoUrl: string;
  city?: string;
  location?: string;
  state: string;
  address: string;
  defaultDashboardPath?: string;
};

type TutorData = {
  status?: string;
  fullName?: string;
  firstName?: string;
  middleName?: string;
  lastName?: string;
  mobileNumber?: string;
  dateOfBirth?: string | null;
  countryOfBirth?: string;
  nationality?: string;
  stateOfOrigin?: string;
  lgaOfOrigin?: string;
  homeState?: string;
  homeCity?: string;
  homeAddress?: string;
  qualification?: string;
  ninNumber?: string;
  bvnNumber?: string;
  profilePhotoUrl?: string;
  documentUrls?: string[];
};

type TutorProfileResponse = {
  headline: string;
  bio: string;
  subjects: string[];
  languages: string[];
  hourlyRate: number;
  profilePhotoUrl?: string;
  gender?: string;
  homeCity?: string;
  homeState?: string;
  homeAddress?: string;
  stateOfOrigin?: string;
  lgaOfOrigin?: string;
  qualification?: string;
  verificationStatus: string;
  isListed: boolean;
  firstLessonFree?: boolean;
  offersFaceToFace?: boolean;
  offersWebcam?: boolean;
  teachingModes?: string[];
  videoCallUrl?: string | null;
  additionalDocumentUrls?: string[];
};

type MobileChangeRequest = {
  id: string;
  requestedMobile: string;
  submittedAt: string;
  status: string;
};

type Notification = {
  type: "success" | "error";
  message: string;
};

type ProfileSubmissionStatus = "unsubmitted" | "submitted" | "approved";

const STUDENT_EDUCATION_LEVELS = [
  "Primary",
  "Secondary",
  "Polytechnic",
  "University (Undergraduate)",
  "University (Postgraduate)",
  "University (Doctorate)",
];

const PROFILE_STATUS_PRESENTATION: Record<
  ProfileSubmissionStatus,
  { label: string; className: string }
> = {
  unsubmitted: { label: "Unsubmitted", className: "text-red-600" },
  submitted: { label: "Submitted", className: "text-blue-600" },
  approved: { label: "Approved", className: "text-green-600" },
};

function buildSelectOptions(items: string[], placeholder: string, currentValue?: string) {
  const normalizedItems = currentValue?.trim() && !items.includes(currentValue)
    ? [currentValue, ...items]
    : items;
  return [
    { value: "", label: placeholder },
    ...normalizedItems.map((item) => ({ value: item, label: item })),
  ];
}

function splitFullName(value?: string | null) {
  const parts = (value ?? "").trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return { firstName: "", middleName: "", lastName: "" };
  if (parts.length === 1) return { firstName: parts[0], middleName: "", lastName: "" };
  return {
    firstName: parts[0],
    middleName: parts.slice(1, -1).join(" "),
    lastName: parts[parts.length - 1],
  };
}

function resolveNameParts(data: {
  firstName?: string;
  middleName?: string;
  lastName?: string;
  fullName?: string;
}, fallbackFullName = "") {
  if (data.firstName || data.middleName || data.lastName) {
    return {
      firstName: data.firstName || "",
      middleName: data.middleName || "",
      lastName: data.lastName || "",
    };
  }
  return splitFullName(data.fullName || fallbackFullName);
}

function composeFullName(firstName: string, middleName: string, lastName: string) {
  return [firstName, middleName, lastName]
    .map((value) => value.trim())
    .filter(Boolean)
    .join(" ");
}

export function DashboardProfilePage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const updateProfile = useAuthStore((s) => s.updateProfile);
  const userId = useAuthStore((s) => s.userId);
  const [isLoading, setIsLoading] = useState(false);
  const [isFormReady, setIsFormReady] = useState(false);
  const [notification, setNotification] = useState<Notification | null>(null);
  const [me, setMe] = useState<MeResponse | null>(null);
  const [tutorData, setTutorData] = useState<TutorData | null>(null);
  const [tutorProfile, setTutorProfile] = useState<TutorProfileResponse | null>(null);

  const [firstName, setFirstName] = useState("");
  const [middleName, setMiddleName] = useState("");
  const [lastName, setLastName] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [mobileNumber, setMobileNumber] = useState("");
  const [dob, setDob] = useState("");
  const [state, setState] = useState("");
  const [city, setCity] = useState("");
  const [address, setAddress] = useState("");
  const [qualification, setQualification] = useState("");
  const [levelOfEducation, setLevelOfEducation] = useState("");
  const [ninNumber, setNinNumber] = useState("");
  const [bvnNumber, setBvnNumber] = useState("");
  const [stateOfOrigin, setStateOfOrigin] = useState("");
  const [lgaOfOrigin, setLgaOfOrigin] = useState("");
  const [headline, setHeadline] = useState("");
  const [bio, setBio] = useState("");
  const [selectedSubjects, setSelectedSubjects] = useState<string[]>([]);
  const [subjectQuery, setSubjectQuery] = useState("");
  const [showSubjectSuggestions, setShowSubjectSuggestions] = useState(false);
  const [selectedLanguages, setSelectedLanguages] = useState<string[]>([]);
  const [languageToAdd, setLanguageToAdd] = useState("");
  const [hourlyRate, setHourlyRate] = useState("");
  const [gender, setGender] = useState("");
  const [firstLessonFree, setFirstLessonFree] = useState(false);
  const [offersFaceToFace, setOffersFaceToFace] = useState(true);
  const [offersWebcam, setOffersWebcam] = useState(false);
  const [uploadingImage, setUploadingImage] = useState(false);

  const [pendingPhotoUrl, setPendingPhotoUrl] = useState<string | null>(null);
  const [previewPhotoUrl, setPreviewPhotoUrl] = useState<string | null>(null);
  const [hasChanges, setHasChanges] = useState(false);
  const [profileSubmissionStatus, setProfileSubmissionStatus] =
    useState<ProfileSubmissionStatus>("unsubmitted");
  const [pendingMobileRequests, setPendingMobileRequests] = useState<MobileChangeRequest[]>([]);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const subjectPickerRef = useRef<HTMLDivElement>(null);
  const clearDraft = useFormDraft(
    userId ? `prepvilla.form-draft.${userId}.profile` : null,
    {
      firstName,
      middleName,
      lastName,
      displayName,
      mobileNumber,
      dob,
      state,
      city,
      address,
      qualification,
      levelOfEducation,
      ninNumber,
      bvnNumber,
      stateOfOrigin,
      lgaOfOrigin,
      headline,
      bio,
      selectedSubjects,
      subjectQuery,
      selectedLanguages,
      languageToAdd,
      hourlyRate,
      gender,
      firstLessonFree,
      offersFaceToFace,
      offersWebcam,
      pendingPhotoUrl,
    },
    (draft) => {
      const hasVerifiedTutorIdentity =
        (me?.role === "tutor" &&
          ["approved", "verified"].includes(tutorProfile?.verificationStatus?.toLowerCase() ?? "")) ||
        (me?.role === "student" &&
          ["approved", "verified"].includes(tutorData?.status?.toLowerCase() ?? ""));
      const canRestoreTutorResidence =
        me?.role === "tutor" &&
        ["approved", "verified"].includes(tutorProfile?.verificationStatus?.toLowerCase() ?? "") &&
        !tutorProfile?.isListed;
      const residenceFields = new Set(["state", "city", "address"]);
      const lockedVerifiedFields = new Set([
        "firstName",
        "middleName",
        "lastName",
        "displayName",
        "mobileNumber",
        "dob",
        "state",
        "city",
        "address",
        "qualification",
        "ninNumber",
        "bvnNumber",
        "stateOfOrigin",
        "lgaOfOrigin",
      ]);
      const currentValues: Record<string, unknown> = {
        firstName,
        middleName,
        lastName,
        displayName,
        mobileNumber,
        dob,
        state,
        city,
        address,
        qualification,
        levelOfEducation,
        ninNumber,
        bvnNumber,
        stateOfOrigin,
        lgaOfOrigin,
        headline,
        bio,
        selectedSubjects,
        subjectQuery,
        selectedLanguages,
        languageToAdd,
        hourlyRate,
        gender,
        firstLessonFree,
        offersFaceToFace,
        offersWebcam,
        pendingPhotoUrl,
      };
      const hasDraftChanges = Object.entries(draft).some(
        ([field, draftValue]) =>
          !(
            hasVerifiedTutorIdentity &&
            lockedVerifiedFields.has(field) &&
            !(canRestoreTutorResidence && residenceFields.has(field))
          ) &&
          JSON.stringify(draftValue) !== JSON.stringify(currentValues[field]),
      );
      if (!hasVerifiedTutorIdentity) {
        if (typeof draft.firstName === "string") setFirstName(draft.firstName);
        if (typeof draft.middleName === "string") setMiddleName(draft.middleName);
        if (typeof draft.lastName === "string") setLastName(draft.lastName);
        if (typeof draft.displayName === "string") setDisplayName(draft.displayName);
        if (typeof draft.mobileNumber === "string") setMobileNumber(draft.mobileNumber);
        if (typeof draft.dob === "string") setDob(draft.dob);
        if (typeof draft.state === "string") setState(draft.state);
        if (typeof draft.city === "string") setCity(draft.city);
        if (typeof draft.address === "string") setAddress(draft.address);
        if (typeof draft.qualification === "string") setQualification(draft.qualification);
        if (typeof draft.ninNumber === "string") setNinNumber(draft.ninNumber);
        if (typeof draft.bvnNumber === "string") setBvnNumber(draft.bvnNumber);
        if (typeof draft.stateOfOrigin === "string") setStateOfOrigin(draft.stateOfOrigin);
        if (typeof draft.lgaOfOrigin === "string") setLgaOfOrigin(draft.lgaOfOrigin);
      } else if (canRestoreTutorResidence) {
        if (typeof draft.state === "string") setState(draft.state);
        if (typeof draft.city === "string") setCity(draft.city);
        if (typeof draft.address === "string") setAddress(draft.address);
      }
      if (typeof draft.headline === "string") setHeadline(draft.headline);
      if (typeof draft.levelOfEducation === "string") setLevelOfEducation(draft.levelOfEducation);
      if (typeof draft.bio === "string") setBio(draft.bio);
      if (Array.isArray(draft.selectedSubjects)) {
        setSelectedSubjects(draft.selectedSubjects.filter((item): item is string => typeof item === "string"));
      }
      if (typeof draft.subjectQuery === "string") setSubjectQuery(draft.subjectQuery);
      if (Array.isArray(draft.selectedLanguages)) {
        setSelectedLanguages(draft.selectedLanguages.filter((item): item is string => typeof item === "string"));
      }
      if (typeof draft.languageToAdd === "string") setLanguageToAdd(draft.languageToAdd);
      if (typeof draft.hourlyRate === "string") setHourlyRate(draft.hourlyRate);
      const hasStoredGender = me?.role === "tutor"
        ? Boolean(tutorProfile?.gender?.trim())
        : Boolean(me?.gender?.trim());
      if (!hasStoredGender && typeof draft.gender === "string") setGender(draft.gender);
      if (typeof draft.firstLessonFree === "boolean") setFirstLessonFree(draft.firstLessonFree);
      if (typeof draft.offersFaceToFace === "boolean") setOffersFaceToFace(draft.offersFaceToFace);
      if (typeof draft.offersWebcam === "boolean") setOffersWebcam(draft.offersWebcam);
      if (typeof draft.pendingPhotoUrl === "string" || draft.pendingPhotoUrl === null) {
        setPendingPhotoUrl(draft.pendingPhotoUrl);
      }
      setHasChanges(hasDraftChanges);
    },
    isFormReady,
  );
  const editMode = searchParams.get("edit") === "profile";
  const verificationStatus = tutorProfile?.verificationStatus?.toLowerCase() ?? "";
  const isApprovedTutorProfile =
    me?.role === "tutor" && (verificationStatus === "approved" || verificationStatus === "verified");
  const isTutor = me?.role === "tutor";
  const isStudent = me?.role === "student";
  const studentVerificationStatus = isStudent ? tutorData?.status?.toLowerCase() ?? "" : "";
  const isApprovedStudentProfile =
    isStudent && (studentVerificationStatus === "approved" || studentVerificationStatus === "verified");
  const hasVerifiedIdentity = isApprovedTutorProfile || isApprovedStudentProfile;
  const hasCompletedTutorProfile = Boolean(tutorProfile?.isListed);
  const canTutorCompleteInitialProfile = isTutor && isApprovedTutorProfile && !hasCompletedTutorProfile;
  const isApprovedTutorEditMode =
    isTutor && isApprovedTutorProfile && hasCompletedTutorProfile && editMode;
  const canEditVerificationBackedTutorFields = !hasVerifiedIdentity;
  const canEditLockedTutorIdentityFields = canEditVerificationBackedTutorFields;
  const canEditTutorPublicProfileFields =
    !isTutor || canTutorCompleteInitialProfile || isApprovedTutorEditMode;
  const hasSubmittedGender = isTutor
    ? Boolean(tutorProfile?.gender?.trim())
    : Boolean(me?.gender?.trim());
  const hasCompletedStudentProfile = Boolean(
    isStudent &&
    me?.isStudentProfileComplete &&
    me?.gender?.trim() &&
    me?.profilePhotoUrl?.trim() &&
    STUDENT_EDUCATION_LEVELS.includes(tutorData?.qualification || ""),
  );
  const isApprovedStudentEditMode =
    isStudent && isApprovedStudentProfile && hasCompletedStudentProfile && editMode;
  const canEditStateOfOrigin = canEditVerificationBackedTutorFields;
  const canEditResidenceFields = isTutor
    ? canTutorCompleteInitialProfile
    : !isApprovedStudentProfile;
  const canEditPhoto = isTutor
    ? canTutorCompleteInitialProfile || isApprovedTutorEditMode
    : isStudent && isApprovedStudentProfile && (!hasCompletedStudentProfile || isApprovedStudentEditMode);
  const verifiedFieldHelperText = hasVerifiedIdentity ? "" : undefined;
  const availableCities = useMemo(() => (isStudent && state ? NIGERIA_STATE_CITIES[state] ?? [] : []), [isStudent, state]);
  const stateOptions = useMemo(
    () => buildSelectOptions(NIGERIA_STATES, "Select State"),
    []
  );
  const stateOfOriginOptions = useMemo(
    () => buildSelectOptions(NIGERIA_STATES, "Select State of Origin"),
    []
  );
  const cityOptions = useMemo(
    () => buildSelectOptions(availableCities, state ? "Select City" : "Select State first", city),
    [availableCities, city, state]
  );
  const genderOptions = useMemo(
    () => [
      { value: "", label: "Select Gender" },
      { value: "male", label: "Male" },
      { value: "female", label: "Female" },
    ],
    []
  );
  const educationLevelOptions = useMemo(
    () => buildSelectOptions(STUDENT_EDUCATION_LEVELS, "Select Level of Education", levelOfEducation),
    [levelOfEducation],
  );
  const languageOptions = useMemo(
    () =>
      buildSelectOptions(
        WORLD_LANGUAGES.filter((language) => !selectedLanguages.includes(language)),
        selectedLanguages.length === WORLD_LANGUAGES.length ? "All listed languages selected" : "Choose Language(s) of Communications",
      ),
    [selectedLanguages],
  );
  const ninNumberError =
    ninNumber.trim() && isTutor && canEditVerificationBackedTutorFields ? getNinNumberError(ninNumber) : null;
  const bvnNumberError =
    bvnNumber.trim() && isTutor && canEditVerificationBackedTutorFields ? getBvnNumberError(bvnNumber) : null;

  const showNotification = useCallback((type: "success" | "error", message: string) => {
    setNotification({ type, message });
    // Auto-dismiss after 5 seconds
    setTimeout(() => setNotification(null), 5000);
  }, []);

  function resolveMediaUrl(pathOrUrl?: string) {
    if (!pathOrUrl) return "";
    if (pathOrUrl.startsWith("http://") || pathOrUrl.startsWith("https://")) return pathOrUrl;
    const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8500";
    return `${baseUrl}${pathOrUrl.startsWith("/") ? "" : "/"}${pathOrUrl}`;
  }

  const filteredSubjectSuggestions = useMemo(() => {
    const query = subjectQuery.trim().toLowerCase();
    return NIGERIAN_SCHOOL_SUBJECTS
      .filter((option) => {
        if (selectedSubjects.includes(option)) return false;
        if (!query) return true;
        return option.toLowerCase().includes(query);
      })
      .slice(0, 8);
  }, [selectedSubjects, subjectQuery]);

  function addSubject(subject: string) {
    setSelectedSubjects((prev) => (prev.includes(subject) ? prev : [...prev, subject]));
    setSubjectQuery("");
    setShowSubjectSuggestions(true);
    setHasChanges(true);
  }

  function removeSubject(subject: string) {
    setSelectedSubjects((prev) => prev.filter((item) => item !== subject));
    setHasChanges(true);
  }

  function addLanguage(language: string) {
    const normalized = language.trim();
    if (!normalized) return;
    setSelectedLanguages((prev) => (prev.includes(normalized) ? prev : [...prev, normalized]));
    setLanguageToAdd("");
    setHasChanges(true);
  }

  function removeLanguage(language: string) {
    setSelectedLanguages((prev) => prev.filter((item) => item !== language));
    setHasChanges(true);
  }

  function handleStudentStateChange(nextState: string) {
    setState(nextState);
    if (!nextState || !(NIGERIA_STATE_CITIES[nextState] ?? []).includes(city)) {
      setCity("");
    }
    setHasChanges(true);
  }

  const load = useCallback(async () => {
    setIsLoading(true);
    setNotification(null);
    const res = await api.get<MeResponse>("/api/me");
    if (!res.ok) {
      showNotification("error", res.error || "Failed to load profile");
      setIsLoading(false);
      setIsFormReady(true);
      return;
    }
    setMe(res.data);
    const meNames = resolveNameParts(res.data);
    setFirstName(meNames.firstName);
    setMiddleName(meNames.middleName);
    setLastName(meNames.lastName);
    setDisplayName(res.data.displayName);
    setMobileNumber(res.data.mobileNumber || "");
    setDob(res.data.dateOfBirth || "");
    setGender(res.data.gender || "");
    const rawState = res.data.state || "";
    const rawCity = res.data.city || res.data.location || "";
    if (res.data.role === "student") {
      const normalizedState = NIGERIA_STATES.includes(rawState) ? rawState : "";
      const normalizedCity =
        normalizedState && (NIGERIA_STATE_CITIES[normalizedState] ?? []).includes(rawCity) ? rawCity : "";
      setState(normalizedState);
      setCity(normalizedCity);
    } else {
      setState(rawState);
      setCity(rawCity);
    }
    setAddress(res.data.address || "");
    setPendingPhotoUrl(null);
    setPreviewPhotoUrl(null);
    setHasChanges(false);

    if (res.data.role === "student") {
      const resStudent = await api.get<TutorData>("/api/students/verification");
      if (resStudent.ok) {
        const studentNames = resolveNameParts(resStudent.data, res.data.fullName);
        setTutorData(resStudent.data);
        setFirstName(studentNames.firstName);
        setMiddleName(studentNames.middleName);
        setLastName(studentNames.lastName);
        setMobileNumber(resStudent.data.mobileNumber || res.data.mobileNumber || "");
        setDob(resStudent.data.dateOfBirth || res.data.dateOfBirth || "");
        setLevelOfEducation(resStudent.data.qualification || "");
        setNinNumber(resStudent.data.ninNumber || "");
        setBvnNumber(resStudent.data.bvnNumber || "");
        setStateOfOrigin(resStudent.data.stateOfOrigin || "");
        setLgaOfOrigin(resStudent.data.lgaOfOrigin || "");
        setState(resStudent.data.homeState || res.data.state || "");
        setCity(resStudent.data.homeCity || res.data.city || res.data.location || "");
        setAddress(resStudent.data.homeAddress || res.data.address || "");
      }
    } else if (res.data.role === "tutor") {
      const resTutor = await api.get<TutorData>("/api/tutors/me/verification");
      const verificationData = resTutor.ok ? resTutor.data : null;
      if (resTutor.ok) {
        const tutorNames = resolveNameParts(resTutor.data, res.data.fullName);
        setTutorData(resTutor.data);
        setFirstName(tutorNames.firstName);
        setMiddleName(tutorNames.middleName);
        setLastName(tutorNames.lastName);
        setMobileNumber(resTutor.data.mobileNumber || res.data.mobileNumber || "");
        setDob(resTutor.data.dateOfBirth || res.data.dateOfBirth || "");
        setQualification(resTutor.data.qualification || "");
        setNinNumber(resTutor.data.ninNumber || "");
        setBvnNumber(resTutor.data.bvnNumber || "");
        setStateOfOrigin(resTutor.data.stateOfOrigin || "");
        setLgaOfOrigin(resTutor.data.lgaOfOrigin || "");
        setState(resTutor.data.homeState || res.data.state || "");
        setCity(resTutor.data.homeCity || res.data.city || res.data.location || "");
        setAddress(resTutor.data.homeAddress || res.data.address || "");
      }
      const resTutorProfile = await api.get<TutorProfileResponse>("/api/tutors/me/profile");
      if (resTutorProfile.ok) {
        const tutorState = resTutorProfile.data.homeState || verificationData?.homeState || res.data.state || "";
        const normalizedTutorState = NIGERIA_STATES.includes(tutorState)
          ? tutorState
          : "";
        setTutorProfile(resTutorProfile.data);
        setProfileSubmissionStatus(resTutorProfile.data.isListed ? "approved" : "unsubmitted");
        setHeadline(resTutorProfile.data.headline || "");
        setBio(resTutorProfile.data.bio || "");
        setSelectedSubjects(resTutorProfile.data.subjects || []);
        setSelectedLanguages(resTutorProfile.data.languages || []);
        setHourlyRate(String(resTutorProfile.data.hourlyRate ?? ""));
        setGender(resTutorProfile.data.gender || "");
        setState(normalizedTutorState);
        setCity(resTutorProfile.data.homeCity || verificationData?.homeCity || res.data.city || res.data.location || "");
        setAddress(resTutorProfile.data.homeAddress || verificationData?.homeAddress || res.data.address || "");
        setStateOfOrigin(resTutorProfile.data.stateOfOrigin || verificationData?.stateOfOrigin || "");
        setLgaOfOrigin(resTutorProfile.data.lgaOfOrigin || verificationData?.lgaOfOrigin || "");
        setFirstLessonFree(Boolean(resTutorProfile.data.firstLessonFree));
        setOffersFaceToFace(resTutorProfile.data.offersFaceToFace ?? !resTutorProfile.data.offersWebcam);
        setOffersWebcam(Boolean(resTutorProfile.data.offersWebcam));
      }
    }
    setIsLoading(false);
    setIsFormReady(true);
  }, [showNotification]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (!isTutor || !tutorProfile || isApprovedTutorProfile) return;
    router.replace("/dashboard/verification");
  }, [isApprovedTutorProfile, isTutor, router, tutorProfile]);

  useEffect(() => {
    if (!isStudent || !tutorData || isApprovedStudentProfile) return;
    router.replace("/dashboard/student-verification");
  }, [isApprovedStudentProfile, isStudent, router, tutorData]);

  useEffect(() => {
    if (me?.role === "student" || me?.role === "tutor") {
      api.get<{ requests: MobileChangeRequest[] }>("/api/me/mobile-change-requests").then((res) => {
        if (res.ok) {
          setPendingMobileRequests(res.data.requests.filter((r) => r.status === "pending"));
        }
      });
    }
  }, [me?.role]);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (!subjectPickerRef.current) return;
      if (!subjectPickerRef.current.contains(event.target as Node)) {
        setShowSubjectSuggestions(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  async function handleImageUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;

    // Only allow images
    if (!file.type.startsWith("image/")) {
      showNotification("error", "Please upload an image file");
      return;
    }

    // Max 5MB
    if (file.size > 5 * 1024 * 1024) {
      showNotification("error", "Image must be less than 5MB");
      return;
    }

    setUploadingImage(true);
    setNotification(null);

    // Create preview URL for immediate display
    const previewUrl = URL.createObjectURL(file);
    setPreviewPhotoUrl(previewUrl);

    const formData = new FormData();
    formData.append("file", file);
    formData.append("kind", "photo");
    const loc = [city, state].map((s) => s.trim()).filter(Boolean).join("_") || "unknown";
    formData.append("location", loc);

    const res = await api.post<{ url: string; name: string; contentType: string | null; size: number | null }>(
      "/api/uploads",
      formData
    );

    if (!res.ok) {
      showNotification("error", res.error || "Failed to upload image");
      setUploadingImage(false);
      setPreviewPhotoUrl(null);
      URL.revokeObjectURL(previewUrl); // Clean up
      return;
    }

    // Upload success
    setPendingPhotoUrl(res.data.url);
    setHasChanges(true);
    setUploadingImage(false);
    setPreviewPhotoUrl(null);
    URL.revokeObjectURL(previewUrl); // Clean up
    showNotification("success", "Photo uploaded. Click 'Save Changes' to apply.");
  }

  function triggerFileInput() {
    fileInputRef.current?.click();
  }

  async function saveProfile() {
    if (!me) return;
    if (isTutor && (!isApprovedTutorProfile || (hasCompletedTutorProfile && !isApprovedTutorEditMode))) {
      return;
    }

    setIsLoading(true);
    setNotification(null);
    const fullName = composeFullName(firstName, middleName, lastName);

    // Validate the remaining student profile fields. Identity fields were locked
    // when verification succeeded and are intentionally not resubmitted here.
    if (me.role === "student") {
      if (!isApprovedStudentProfile) {
        router.replace("/dashboard/student-verification");
        setIsLoading(false);
        return;
      }
      if (!gender.trim()) {
        showNotification("error", "Gender is required");
        setIsLoading(false);
        return;
      }
      if (!levelOfEducation.trim()) {
        showNotification("error", "Level of Education is required");
        setIsLoading(false);
        return;
      }
      const profilePhotoUrl = pendingPhotoUrl || currentPhotoUrl || "";
      if (!profilePhotoUrl) {
        showNotification("error", "Profile photo is required");
        setIsLoading(false);
        return;
      }
      const profileRes = await api.put<MeResponse>("/api/me", {
        displayName,
        gender,
        levelOfEducation,
        profilePhotoUrl,
        completeProfile: true,
      });
      if (!profileRes.ok) {
        showNotification("error", profileRes.error || "Failed to complete profile");
        setIsLoading(false);
        return;
      }
      setMe(profileRes.data);
      setTutorData((current) => ({
        ...(current || {}),
        qualification: levelOfEducation,
        profilePhotoUrl,
      }));
      updateProfile({ displayName: profileRes.data.displayName });
      setPendingPhotoUrl(null);
      setHasChanges(false);
      setIsLoading(false);
      clearDraft();
      router.replace(isApprovedStudentEditMode ? "/dashboard/profile" : profileRes.data.defaultDashboardPath || "/search");
      return;
    }

    if (me.role === "tutor" && canEditVerificationBackedTutorFields) {
      if (!state.trim() || !city.trim() || !address.trim()) {
        showNotification("error", "Home state, home city, and home address are required");
        setIsLoading(false);
        return;
      }
      if (canTutorCompleteInitialProfile && (!stateOfOrigin.trim() || !lgaOfOrigin.trim())) {
        showNotification("error", "State and LGA of origin are required");
        setIsLoading(false);
        return;
      }
      const verificationRes = await api.post<TutorData>("/api/tutors/me/verification", {
        firstName,
        middleName,
        lastName,
        fullName,
        mobileNumber,
        dateOfBirth: dob,
        homeState: state,
        homeCity: city,
        homeAddress: address,
        stateOfOrigin,
        lgaOfOrigin,
        qualification,
        ninNumber,
        bvnNumber,
        profilePhotoUrl: pendingPhotoUrl || currentPhotoUrl || "",
        documentUrls: tutorData?.documentUrls ?? [],
      });
      if (!verificationRes.ok) {
        showNotification("error", verificationRes.error || "Failed to save verification-backed tutor details");
        setIsLoading(false);
        return;
      }
      setTutorData(verificationRes.data);
      setQualification(verificationRes.data.qualification || "");
      setNinNumber(verificationRes.data.ninNumber || "");
      setBvnNumber(verificationRes.data.bvnNumber || "");
    }

    // Prepare basic update data (exclude mobile number if it requires approval)
    const basicUpdateData: Record<string, string> = {
      displayName,
    };
    if (!isTutor) {
      basicUpdateData.location = city;
      basicUpdateData.state = state;
      basicUpdateData.address = address;
    }
    if (!isTutor && mobileNumber !== (me.mobileNumber || "")) {
      basicUpdateData.mobileNumber = mobileNumber;
    }

    // 1. Save basic info
    const basicRes = await api.put<MeResponse>("/api/me", basicUpdateData);
    if (!basicRes.ok) {
      showNotification("error", basicRes.error || "Failed to save basic info");
      setIsLoading(false);
      return;
    }
    setMe(basicRes.data);
    updateProfile({ displayName: basicRes.data.displayName });

    // 3. Save tutor profile (includes photo if changed)
    if (me.role === "tutor") {
      if (canTutorCompleteInitialProfile && (!state.trim() || !city.trim() || !address.trim())) {
        showNotification("error", "Country, state, city, and address are required");
        setIsLoading(false);
        return;
      }
      if (!offersFaceToFace && !offersWebcam) {
        showNotification("error", "Select at least one teaching method");
        setIsLoading(false);
        return;
      }
      const rate = hourlyRate.trim() ? Number(hourlyRate) : 0;

      const tutorSaveData: Record<string, unknown> = {
        headline,
        bio,
        subjects: selectedSubjects,
        languages: selectedLanguages,
        hourlyRate: Math.round(rate),
        firstLessonFree,
        offersFaceToFace,
        offersWebcam,
      };

      if (canTutorCompleteInitialProfile) {
        tutorSaveData.homeState = state;
        tutorSaveData.homeCity = city;
        tutorSaveData.homeAddress = address;
      }

      if (canEditTutorPublicProfileFields && !hasSubmittedGender) {
        tutorSaveData.gender = gender;
      }
      if (canEditStateOfOrigin) {
        tutorSaveData.stateOfOrigin = stateOfOrigin;
        tutorSaveData.lgaOfOrigin = lgaOfOrigin;
      }

      // Include photo URL if there's a pending change
      if (pendingPhotoUrl && canEditPhoto) {
        tutorSaveData.profilePhotoUrl = pendingPhotoUrl;
      }

      setProfileSubmissionStatus("submitted");
      const tutorRes = await api.put<TutorProfileResponse>("/api/tutors/me/profile", tutorSaveData);
      if (!tutorRes.ok) {
        showNotification("error", tutorRes.error || "Failed to save tutor profile");
        setIsLoading(false);
        return;
      }
      setTutorProfile(tutorRes.data);
      setProfileSubmissionStatus(tutorRes.data.isListed ? "approved" : "submitted");
    }

    // Clear pending changes and reload
    setPendingPhotoUrl(null);
    setHasChanges(false);
    setIsLoading(false);
    clearDraft();

    showNotification("success", "Changes saved successfully!");

    // Re-fetch tutor data to get the updated photo URL
    if (me.role === "tutor") {
      const resTutor = await api.get<TutorData>("/api/tutors/me/verification");
      if (resTutor.ok && resTutor.data) {
        setTutorData(resTutor.data);
      }
      const resTutorProfile = await api.get<TutorProfileResponse>("/api/tutors/me/profile");
      if (resTutorProfile.ok && resTutorProfile.data) {
        setTutorProfile(resTutorProfile.data);
        setProfileSubmissionStatus(resTutorProfile.data.isListed ? "approved" : "unsubmitted");
      }
    }

    if (isTutor && isApprovedTutorProfile) {
      router.replace("/dashboard/profile");
    }

    // Trigger refresh on home page
    if (typeof window !== 'undefined') {
      window.dispatchEvent(new CustomEvent('refresh-home-tutors'));
    }
  }

  // Get the current or pending photo URL
  const currentPhotoUrl = previewPhotoUrl || pendingPhotoUrl || (
    isTutor
      ? tutorData?.profilePhotoUrl || tutorProfile?.profilePhotoUrl || me?.profilePhotoUrl
      : tutorData?.profilePhotoUrl || me?.profilePhotoUrl
  );

  return (
    <div className="grid gap-4">
      {/* Notification */}
      {notification && (
        <div className={`rounded-xl p-4 text-[14px] leading-[22px] ${notification.type === "success"
          ? "bg-green-50 border border-green-200 text-green-800"
          : "bg-red-50 border border-red-200 text-red-800"
          }`}>
          {notification.message}
        </div>
      )}

      <div className="form-panel rounded-2xl p-4">
        <div className="flex items-center justify-between gap-3">
          <div>
            <h1 className="brand-heading text-[24px] font-semibold leading-[32px]">Profile</h1>
            <p className="mt-1 text-[14px] leading-[22px] text-black/65">Manage your profile information.</p>
          </div>
          <div className="flex gap-2">
            <Button variant="secondary" onClick={load} disabled={isLoading}>
              Cancel
            </Button>
            <Button
              onClick={() => void saveProfile()}
              disabled={
                isLoading ||
                !hasChanges ||
                (isTutor && (!isApprovedTutorProfile || (hasCompletedTutorProfile && !isApprovedTutorEditMode)))
              }
            >
              {isLoading ? "Saving..." : isStudent && !hasCompletedStudentProfile ? "Complete Profile" : "Save Changes"}
            </Button>
          </div>
        </div>
      </div>

      {/* {isTutor ? (
        <div className="form-panel rounded-2xl px-4 py-3 text-[16px] leading-[24px]">
          <span className="font-medium text-black/65">Profile Status: </span>
          <span className={`font-semibold ${PROFILE_STATUS_PRESENTATION[profileSubmissionStatus].className}`}>
            {PROFILE_STATUS_PRESENTATION[profileSubmissionStatus].label}
          </span>
        </div>
      ) : null} */}

      {isTutor && !isApprovedTutorProfile ? (
        <div className="rounded-2xl border border-info-border bg-info-soft p-4 text-[14px] leading-[22px] text-info-foreground">
          Verification approval is required before you can edit your tutor profile. Redirecting you to the verification page.
        </div>
      ) : null}

      {isStudent && isApprovedStudentProfile && !hasCompletedStudentProfile ? (
        <div className="rounded-2xl border border-green-200 bg-green-50 p-4 text-[14px] leading-[22px] text-green-900">
          Verification Successful, complete your profile.
        </div>
      ) : null}

      {isTutor && isApprovedTutorProfile && !hasCompletedTutorProfile ? (
        <div className="rounded-2xl border border-green-200 bg-green-50 p-4 text-[14px] leading-[22px] text-green-900">
          <span className="text-[18px] font-semibold text-black">Profile Status: </span>
          <span className={`text-[18px] font-semibold ${PROFILE_STATUS_PRESENTATION[profileSubmissionStatus].className}`}>
            {PROFILE_STATUS_PRESENTATION[profileSubmissionStatus].label}
          </span><br />Verification Successful. Complete your tutor profile once to publish it to students.
        </div>
      ) : null}

      {isTutor && isApprovedTutorProfile && hasCompletedTutorProfile && !isApprovedTutorEditMode ? (
        <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4 text-[14px] leading-[22px] text-amber-900">
          <span className="text-[18px] font-semibold text-black">Profile Status: </span>
          <span className={`text-[18px] font-semibold ${PROFILE_STATUS_PRESENTATION[profileSubmissionStatus].className}`}>
            {PROFILE_STATUS_PRESENTATION[profileSubmissionStatus].label}
          </span><br />To update profile → Go to settings and make the neccessary changes.
        </div>
      ) : null}

      {isTutor && isApprovedTutorEditMode ? (
        <div className="rounded-2xl border border-info-border bg-info-soft p-4 text-[14px] leading-[22px] text-info-foreground">
          Only non sensitive fields are editable, to update sensitive data, please contact support on the{" "}
          <button type="button" onClick={() => router.push("/dashboard/support")} className="font-semibold underline">
            Support page
          </button>
          {" "}.
        </div>
      ) : null}

      {/* Profile Photo Section - For Students and Tutors */}
      {(me?.role === "student" || me?.role === "tutor") && (
        <div className="form-panel rounded-2xl p-6">
          <h2 className="mb-4 text-[18px] font-semibold">Profile Photo</h2>
          <div className="flex items-center gap-6">
            <div className="relative">
              {currentPhotoUrl ? (
                <Image
                  key={currentPhotoUrl}
                  className="h-32 w-32 rounded-full border-4 border-white shadow-lg object-cover"
                  src={resolveMediaUrl(currentPhotoUrl)}
                  alt="Profile photo"
                  width={128}
                  height={128}
                  unoptimized
                />
              ) : (
                <div className="flex h-32 w-32 items-center justify-center rounded-full bg-gradient-to-br from-gray-200 to-gray-300 text-4xl font-medium text-gray-500 border-4 border-white shadow-lg">
                  {me?.displayName?.charAt(0).toUpperCase() || "?"}
                </div>
              )}
              {uploadingImage && (
                <div className="absolute inset-0 flex items-center justify-center bg-black/50 rounded-full">
                  <div className="h-8 w-8 animate-spin rounded-full border-2 border-white border-t-transparent" />
                </div>
              )}
              {pendingPhotoUrl && (
                <div className="absolute -top-2 -right-2 bg-green-500 text-white text-xs px-2 py-1 rounded-full">
                  New
                </div>
              )}
            </div>
            <div className="flex-1">
              {/* <p className="mb-3 text-[14px] text-black/65">
                Upload photo.
              </p> */}
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                onChange={handleImageUpload}
                className="hidden"
                disabled={!canEditPhoto}
              />
              {canEditPhoto &&
                <Button
                  variant="secondary"
                  onClick={triggerFileInput}
                  disabled={uploadingImage || !canEditPhoto}
                >
                  {uploadingImage ? "Uploading..." : currentPhotoUrl ? "Change Photo" : "Upload Photo"}
                </Button>
              }

            </div>
          </div>
        </div>
      )}

      <div className="form-panel rounded-2xl p-4">
        <div className="mb-4 grid gap-4 md:grid-cols-2">
          <div className="md:col-span-2">
            <h2 className="mb-3 text-[18px] font-semibold">Basic Information</h2>
          </div>
          <div className="grid gap-4 md:col-span-2 md:grid-cols-3">
            <Input
              label="First name"
              value={firstName}
              onChange={(e) => {
                setFirstName(e.target.value);
                setHasChanges(true);
              }}
              disabled={hasVerifiedIdentity}
              helperText={verifiedFieldHelperText}
            />
            <Input
              label="Middle name"
              value={middleName}
              onChange={(e) => {
                setMiddleName(e.target.value);
                setHasChanges(true);
              }}
              disabled={hasVerifiedIdentity}
              helperText={verifiedFieldHelperText}
            />
            <Input
              label="Last name"
              value={lastName}
              onChange={(e) => {
                setLastName(e.target.value);
                setHasChanges(true);
              }}
              disabled={hasVerifiedIdentity}
              helperText={verifiedFieldHelperText}
            />
          </div>
          <div className="grid gap-4 md:col-span-2 md:grid-cols-3">
            {isStudent ? (
              <Select
                label="Home State"
                labelClassName="mb-1 text-sm !leading-5"
                className="h-11"
                value={state}
                onChange={(e) => handleStudentStateChange(e.target.value)}
                options={stateOptions}
                disabled={!canEditVerificationBackedTutorFields}
              />
            ) : null}

            {isStudent ? (
              <Select
                label="Home City"
                labelClassName="mb-1 text-sm !leading-5"
                className="h-11"
                value={city}
                onChange={(e) => {
                  setCity(e.target.value);
                  setHasChanges(true);
                }}
                options={cityOptions}
                disabled={!canEditVerificationBackedTutorFields || !state}
              />
            ) : null}
            {isStudent ? (
              <Input
                label="Home Address"
                value={address}
                onChange={(e) => {
                  setAddress(e.target.value);
                  setHasChanges(true);
                }}
                disabled={!canEditVerificationBackedTutorFields}
                placeholder="Full address"
              />
            ) : null}
          </div>

          {isStudent ? (
            <Select
              label="Level of Education *"
              labelClassName="mb-1 text-sm !leading-5"
              className="h-11"
              value={levelOfEducation}
              onChange={(e) => {
                setLevelOfEducation(e.target.value);
                setHasChanges(true);
              }}
              options={educationLevelOptions}
              disabled={!canEditPhoto}
              required
            />
          ) : null}


        </div>

        <div className="mb-4 grid gap-4 md:grid-cols-3">


          <Input
            label="Email Address"
            value={me?.email || ""}
            disabled
          // helperText="Change securely in Settings with an email OTP."
          />

          <Input
            label="Mobile Number"
            value={mobileNumber}
            onChange={(e) => {
              setMobileNumber(sanitizeMobileNumberInput(e.target.value));
              setHasChanges(true);
            }}
            disabled
            placeholder="+2348012345678"
          // helperText="Change securely in Settings with an email OTP."
          />

          <Input
            label="Display Name"
            value={displayName}
            onChange={(e) => {
              setDisplayName(e.target.value);
              setHasChanges(true);
            }}
            disabled={isTutor && !canEditVerificationBackedTutorFields}
          // helperText={isTutor ? verifiedFieldHelperText : "Choose the name tutors will see."}
          />
        </div>

        {isTutor ? (
          <div className="mb-4 border-t border-border pt-4">
            <div className="mb-4">
              <h2 className="text-[18px] font-semibold">Residence</h2>
              <p className="mt-1 text-xs leading-[20px] text-black/55">
                Provide your current residential details.
              </p>
            </div>
            <div className="mb-4 grid gap-4 md:grid-cols-3">
              <Input label="Country *" value="Nigeria" disabled />
              <Select
                label="State *"
                labelClassName="mb-1 text-sm !leading-5"
                className="h-11"
                value={state}
                onChange={(e) => {
                  setState(e.target.value);
                  setHasChanges(true);
                }}
                options={stateOptions}
                disabled={!canEditResidenceFields}
                required
              />
              <Input
                label="City *"
                value={city}
                onChange={(e) => {
                  setCity(e.target.value);
                  setHasChanges(true);
                }}
                disabled={!canEditResidenceFields}
                placeholder="e.g. Lagos"
                required
              />
            </div>
            <div className="mb-4 grid gap-4 md:grid-cols-1">
              <Input
                label="Address *"
                value={address}
                onChange={(e) => {
                  setAddress(e.target.value);
                  setHasChanges(true);
                }}
                disabled={!canEditResidenceFields}
                placeholder="Full residential address"
                required
              />
            </div>
          </div>
        ) : null}

        {isTutor ? (
          <div className="mb-4 grid gap-4 md:grid-cols-2">
            <Select
              label="State of Origin"
              labelClassName="mb-1 text-sm !leading-5"
              className="h-11"
              value={stateOfOrigin}
              onChange={(e) => {
                setStateOfOrigin(e.target.value);
                setHasChanges(true);
              }}
              options={stateOfOriginOptions}
              disabled={!canEditStateOfOrigin}
            />
            <Input
              label="LGA of Origin"
              value={lgaOfOrigin}
              onChange={(e) => {
                setLgaOfOrigin(e.target.value);
                setHasChanges(true);
              }}
              disabled={!canEditStateOfOrigin}
              placeholder="e.g. Ikeja"
            />
          </div>
        ) : null}

        <div className="mb-4 grid gap-4 md:grid-cols-3">
          {pendingMobileRequests.length > 0 && (
            <div className="rounded-xl border border-orange-200 bg-orange-50 p-4">
              <h4 className="text-[14px] font-semibold text-orange-800 mb-2">Pending Mobile Number Change</h4>
              {pendingMobileRequests.map((request) => (
                <div key={request.id} className="text-[12px] text-orange-700">
                  <div>Requested: {request.requestedMobile}</div>
                  <div>Submitted: {new Date(request.submittedAt).toLocaleDateString()}</div>
                  <div className="mt-1 text-orange-600">Status: Awaiting admin approval</div>
                </div>
              ))}
            </div>
          )}

          <Input
            label="Date of Birth"
            type="date"
            value={dob}
            onChange={(e) => {
              setDob(e.target.value);
              setHasChanges(true);
            }}
            disabled={isTutor ? !canEditLockedTutorIdentityFields : !!me?.dateOfBirth}
            helperText={verifiedFieldHelperText}
          />

          <div className="grid gap-1">
            <Select
              label="Gender"
              labelClassName="mb-1 text-sm !leading-5"
              className="h-11"
              value={gender}
              onChange={(e) => {
                setGender(e.target.value);
                setHasChanges(true);
              }}
              options={genderOptions}
              disabled={!canEditTutorPublicProfileFields || hasSubmittedGender}
            />
            <p className="text-[12px] leading-[18px] text-black/55">
              {hasSubmittedGender
                ? isTutor
                  ? "Gender is locked after submission. Request a correction through Support; only an administrator can change it."
                  : "Gender is locked after submission. Contact an administrator to request a correction."
                : ""}
            </p>
            {hasSubmittedGender && isTutor ? (
              <div className="mt-1">
                <Button variant="ghost" onClick={() => router.push("/dashboard/support")}>
                  Request Gender Correction
                </Button>
              </div>
            ) : null}
          </div>

          <Input
            label="Qualification"
            value={qualification}
            onChange={(e) => {
              setQualification(e.target.value);
              setHasChanges(true);
            }}
            disabled
          // helperText="Change securely in Settings with an email OTP."
          />
        </div>

        <div className="mb-4 grid gap-4">
          {tutorData && (
            <div className="contents">
              <div className="md:col-span-2 mt-4 border-t border-border pt-4">
                <h2 className="mb-3 text-[18px] font-semibold">Verification Details</h2>
              </div>
              <div className="grid gap-4 md:col-span-2 md:grid-cols-2">
                <Input
                  label="NIN Number"
                  value={ninNumber}
                  onChange={(e) => {
                    setNinNumber(sanitizeNinInput(e.target.value));
                    setHasChanges(true);
                  }}
                  disabled={!canEditLockedTutorIdentityFields}
                  inputMode="numeric"
                  placeholder="12345678901"
                  helperText={verifiedFieldHelperText ?? "NIN must be exactly 11 digits."}
                  error={ninNumberError ?? undefined}
                />

                <Input
                  label="BVN Number *"
                  value={bvnNumber}
                  onChange={(e) => {
                    setBvnNumber(sanitizeBvnInput(e.target.value));
                    setHasChanges(true);
                  }}
                  disabled={!canEditLockedTutorIdentityFields}
                  inputMode="numeric"
                  placeholder="12345678901"
                  helperText={verifiedFieldHelperText ?? "BVN must be exactly 11 digits."}
                  error={bvnNumberError ?? undefined}
                  required
                />

                {isStudent ? (
                  <>
                    <Input label="Country of Birth" value={tutorData.countryOfBirth || ""} disabled helperText={verifiedFieldHelperText} />
                    <Input label="Nationality" value={tutorData.nationality || ""} disabled helperText={verifiedFieldHelperText} />
                    <Input label="State of Origin" value={tutorData.stateOfOrigin || ""} disabled helperText={verifiedFieldHelperText} />
                    <Input label="LGA of Origin" value={tutorData.lgaOfOrigin || ""} disabled helperText={verifiedFieldHelperText} />
                  </>
                ) : null}
              </div>
            </div>
          )}
        </div>
      </div>

      {
        me?.role === "tutor" ? (
          <div className="mb-6 form-panel rounded-2xl p-4">
            <div className="mb-3">
              <h2 className="text-[18px] font-semibold">Tutor Profile</h2>
              <p className="mt-1 text-[14px] leading-[22px] text-black/65">
                This is what students see on your public profile.
              </p>
            </div>
            <div className="grid gap-4 md:grid-cols-2">
              <Input
                label="Headline"
                value={headline}
                onChange={(e) => {
                  setHeadline(e.target.value);
                  setHasChanges(true);
                }}
                disabled={!canEditTutorPublicProfileFields}
                placeholder="e.g. Experienced Maths Teacher"
              />
              <Input
                label="Hourly Rate (₦)"
                type="number"
                inputMode="numeric"
                value={hourlyRate}
                onChange={(e) => {
                  setHourlyRate(e.target.value);
                  setHasChanges(true);
                }}
                disabled={!canEditTutorPublicProfileFields}
                placeholder="e.g. 5000"
              />
              <div className="md:col-span-2">
                <Textarea
                  label="About"
                  labelClassName="mb-1 text-sm !leading-5"
                  value={bio}
                  onChange={(e) => {
                    setBio(e.target.value);
                    setHasChanges(true);
                  }}
                  disabled={!canEditTutorPublicProfileFields}
                  placeholder="Share your experience, teaching style, and what students can expect."
                />
              </div>
              <div className="grid gap-4 md:col-span-2 md:grid-cols-2">
                <div className="relative" ref={subjectPickerRef}>
                  <label className="mb-2 block text-sm font-medium text-foreground">Subjects</label>
                  <div className={`rounded-xl border p-[7px] transition ${canEditTutorPublicProfileFields
                    ? "border-black/12 bg-white focus-within:border-black focus-within:ring-4 focus-within:ring-black/8"
                    : "border-slate-200 bg-slate-100"
                    }`}>
                    {selectedSubjects.length > 0 ? (
                      <div className="mb-2 flex flex-wrap gap-2">
                        {selectedSubjects.map((subject) => (
                          <span
                            key={subject}
                            className="inline-flex items-center gap-1 rounded-full border border-black bg-black px-2.5 py-1 text-xs font-medium text-white"
                          >
                            {subject}
                            <button
                              type="button"
                              onClick={() => removeSubject(subject)}
                              className="text-white/70 hover:text-white disabled:text-white/35"
                              disabled={!canEditTutorPublicProfileFields}
                              aria-label={`Remove ${subject}`}
                            >
                              ×
                            </button>
                          </span>
                        ))}
                      </div>
                    ) : null}
                    <input
                      value={subjectQuery}
                      onFocus={() => {
                        if (canEditTutorPublicProfileFields) {
                          setShowSubjectSuggestions(true);
                        }
                      }}
                      onChange={(e) => {
                        setSubjectQuery(e.target.value);
                        if (canEditTutorPublicProfileFields) {
                          setShowSubjectSuggestions(true);
                        }
                      }}
                      onKeyDown={(e) => {
                        if (canEditTutorPublicProfileFields && e.key === "Enter" && filteredSubjectSuggestions.length > 0) {
                          e.preventDefault();
                          addSubject(filteredSubjectSuggestions[0]);
                        }
                      }}
                      disabled={!canEditTutorPublicProfileFields}
                      placeholder={
                        canEditTutorPublicProfileFields
                          ? "Start typing and matching subjects will appear in the dropdown."
                          : "Subject editing is locked after approval"
                      }
                      className="h-7 w-full rounded-lg border border-transparent bg-transparent px-1 text-xs text-foreground outline-none placeholder:text-muted-foreground disabled:text-slate-500"
                    />
                    {/* {canEditApprovedTutorFields ? (
                  // <p className="px-2 pt-1 text-xs text-muted">
                  //   Start typing and matching subjects will appear in the dropdown below.
                  // </p>
                  null
                ) : null} */}
                  </div>
                  {canEditTutorPublicProfileFields && showSubjectSuggestions && filteredSubjectSuggestions.length > 0 ? (
                    <div className="absolute z-10 mt-2 max-h-56 w-full overflow-auto rounded-xl border border-black/12 bg-white p-1 shadow-[0_18px_36px_rgba(15,23,42,0.1)]">
                      {filteredSubjectSuggestions.map((subject) => (
                        <button
                          key={subject}
                          type="button"
                          onClick={() => addSubject(subject)}
                          className="w-full rounded-lg px-3 py-2 text-left text-sm text-black transition hover:bg-black hover:text-white"
                        >
                          {subject}
                        </button>
                      ))}
                    </div>
                  ) : null}
                </div>
                <div className="grid gap-2">
                  <label className="text-sm font-medium text-foreground">Languages</label>
                  <div className={`rounded-xl border p-[7px] transition ${canEditTutorPublicProfileFields
                    ? "border-black/12 bg-white focus-within:border-black focus-within:ring-4 focus-within:ring-black/8"
                    : "border-slate-200 bg-slate-100"
                    }`}>
                    {selectedLanguages.length > 0 ? (
                      <div className="mb-2 flex flex-wrap gap-2">
                        {selectedLanguages.map((language) => (
                          <span
                            key={language}
                            className="inline-flex items-center gap-1 rounded-full border border-black bg-black px-2.5 py-1 text-xs font-medium text-white"
                          >
                            {language}
                            <button
                              type="button"
                              onClick={() => removeLanguage(language)}
                              className="text-white/70 hover:text-white disabled:text-white/35"
                              disabled={!canEditTutorPublicProfileFields}
                              aria-label={`Remove ${language}`}
                            >
                              ×
                            </button>
                          </span>
                        ))}
                      </div>
                    ) : null}
                    <select
                      value={languageToAdd}
                      onChange={(e) => {
                        const nextLanguage = e.target.value;
                        setLanguageToAdd(nextLanguage);
                        if (nextLanguage) {
                          addLanguage(nextLanguage);
                        }
                      }}
                      className={`h-7 w-full rounded-lg border border-transparent bg-transparent px-1 text-xs outline-none ${languageToAdd ? "text-foreground" : "text-slate-400"
                        } disabled:cursor-not-allowed disabled:text-slate-500`}
                      disabled={!canEditTutorPublicProfileFields || languageOptions.length <= 1}
                    >
                      {languageOptions.map((option) => (
                        <option
                          key={option.value || option.label}
                          value={option.value}
                          className={option.value ? "text-foreground" : "text-slate-400"}
                        >
                          {option.label}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
              </div>


              <div className="rounded-xl border border-border bg-white p-4 md:col-span-2">
                <div className="text-[14px] font-semibold leading-[22px]">Teaching Methods</div>
                <p className="mt-1 text-[12px] leading-[18px] text-black/55">
                  Choose how you can teach students. Face-to-face is enabled by default.
                </p>
                <div className="mt-4 grid gap-4 md:grid-cols-3">
                  <label className={`inline-flex h-full items-start gap-3 rounded-xl border px-3 py-3 text-[14px] leading-[22px] ${!canEditTutorPublicProfileFields ? "border-slate-200 bg-slate-100 text-slate-500" : "border-black/12 bg-white"
                    }`}>
                    <input
                      type="checkbox"
                      checked={offersFaceToFace}
                      onChange={(e) => {
                        setOffersFaceToFace(e.target.checked);
                        setHasChanges(true);
                      }}
                      disabled={!canEditTutorPublicProfileFields}
                      className="mt-1 h-4 w-4 rounded border-border text-accent focus:ring-accent"
                    />
                    <span>
                      Face-to-face
                      <span className="mt-0.5 block text-[12px] text-black/55">
                        Students will see that you offer in-person lessons.
                      </span>
                    </span>
                  </label>
                  <label className={`inline-flex h-full items-start gap-3 rounded-xl border px-3 py-3 text-[14px] leading-[22px] ${!canEditTutorPublicProfileFields ? "border-slate-200 bg-slate-100 text-slate-500" : "border-black/12 bg-white"
                    }`}>
                    <input
                      type="checkbox"
                      checked={offersWebcam}
                      onChange={(e) => {
                        setOffersWebcam(e.target.checked);
                        setHasChanges(true);
                      }}
                      disabled={!canEditTutorPublicProfileFields}
                      className="mt-1 h-4 w-4 rounded border-border text-accent focus:ring-accent"
                    />
                    <span>
                      Webcam
                      <span className="mt-0.5 block text-[12px] text-black/55">
                        Enables online lessons and a video room for webcam bookings.
                      </span>
                    </span>
                  </label>
                  <label className={`inline-flex h-full items-start gap-3 rounded-xl border px-3 py-3 text-[14px] leading-[22px] ${!canEditTutorPublicProfileFields ? "border-slate-200 bg-slate-100 text-slate-500" : "border-black/12 bg-white"
                    }`}>
                    <input
                      type="checkbox"
                      checked={firstLessonFree}
                      onChange={(e) => {
                        setFirstLessonFree(e.target.checked);
                        setHasChanges(true);
                      }}
                      disabled={!canEditTutorPublicProfileFields}
                      className="mt-1 h-4 w-4 rounded border-border text-accent focus:ring-accent"
                    />
                    <span>
                      Offer first lesson for free
                      <span className="mt-0.5 block text-[12px] text-black/55">
                        If enabled, students will see a &quot;First lesson free&quot; label on your tutor card.
                      </span>
                    </span>
                  </label>
                </div>
                {offersWebcam && tutorProfile?.videoCallUrl ? (
                  <div className="mt-3 rounded-xl border border-info-border bg-info-soft px-3 py-3 text-[13px] leading-[20px] text-info-foreground">
                    Webcam lessons are enabled.
                    <button
                      type="button"
                      onClick={() => router.push("/dashboard/video-room")}
                      className="ml-2 font-semibold text-primary-deep underline"
                    >
                      Open video room
                    </button>
                  </div>
                ) : null}
              </div>

              <div className="md:col-span-2 mt-2 flex flex-wrap items-center justify-between gap-2">
                <div className="text-[14px] leading-[18px] text-black/55">
                  {isTutor && isApprovedTutorProfile && hasCompletedTutorProfile && !isApprovedTutorEditMode
                    ? "Profile edit locked → Update via setting"
                    : hasChanges
                      ? "You have unsaved changes"
                      : "All changes saved"}
                </div>
              </div>
            </div>
          </div>
        ) : null
      }
    </div >
  );
}
