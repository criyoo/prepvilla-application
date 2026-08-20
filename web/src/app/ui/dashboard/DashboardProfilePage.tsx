"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Button } from "../shared/Button";
import { Input } from "../shared/Input";
import { Select } from "../shared/Select";
import { Textarea } from "../shared/Textarea";
import { api } from "../shared/api";
import { useAuthStore } from "../shared/authStore";
import { NIGERIAN_SCHOOL_SUBJECTS, NIGERIA_STATE_CITIES, NIGERIA_STATES, WORLD_LANGUAGES } from "../shared/nigeriaData";
import { getMobileNumberError, getBvnNumberError, getNinNumberError, sanitizeMobileNumberInput, sanitizeNinInput, sanitizeBvnInput } from "../shared/profileValidation";
import type { UserRole } from "@prepvilla/types";

type MeResponse = {
  id: string;
  email: string;
  role: UserRole;
  displayName: string;
  timezone: string;
  fullName: string;
  mobileNumber: string;
  dateOfBirth: string | null;
  profilePhotoUrl: string;
  city?: string;
  location?: string;
  state: string;
  address: string;
};

type TutorData = {
  status?: string;
  fullName?: string;
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

function buildSelectOptions(items: string[], placeholder: string) {
  return [
    { value: "", label: placeholder },
    ...items.map((item) => ({ value: item, label: item })),
  ];
}

export function DashboardProfilePage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const updateProfile = useAuthStore((s) => s.updateProfile);
  const [isLoading, setIsLoading] = useState(false);
  const [notification, setNotification] = useState<Notification | null>(null);
  const [me, setMe] = useState<MeResponse | null>(null);
  const [tutorData, setTutorData] = useState<TutorData | null>(null);
  const [tutorProfile, setTutorProfile] = useState<TutorProfileResponse | null>(null);

  const [fullName, setFullName] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [mobileNumber, setMobileNumber] = useState("");
  const [dob, setDob] = useState("");
  const [state, setState] = useState("");
  const [city, setCity] = useState("");
  const [address, setAddress] = useState("");
  const [qualification, setQualification] = useState("");
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
  const [pendingMobileRequests, setPendingMobileRequests] = useState<MobileChangeRequest[]>([]);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const subjectPickerRef = useRef<HTMLDivElement>(null);
  const editMode = searchParams.get("edit") === "profile";
  const verificationStatus = tutorProfile?.verificationStatus?.toLowerCase() ?? "";
  const isApprovedTutorProfile =
    me?.role === "tutor" && (verificationStatus === "approved" || verificationStatus === "verified");
  const isTutor = me?.role === "tutor";
  const hasCompletedTutorProfile = Boolean(tutorProfile?.isListed);
  const isApprovedListedTutor = isTutor && isApprovedTutorProfile && hasCompletedTutorProfile;
  const canTutorCompleteInitialProfile = isTutor && isApprovedTutorProfile && !hasCompletedTutorProfile;
  const isApprovedTutorEditMode =
    isTutor && isApprovedTutorProfile && hasCompletedTutorProfile && editMode;
  const canEditVerificationBackedTutorFields =
    !isTutor || canTutorCompleteInitialProfile || isApprovedTutorEditMode;
  const canEditLockedTutorIdentityFields = !isApprovedListedTutor;
  const canEditTutorPublicProfileFields =
    !isTutor || canTutorCompleteInitialProfile || isApprovedTutorEditMode;
  const hasSubmittedGender = isTutor && Boolean(tutorProfile?.gender?.trim());
  const canEditStateOfOrigin = !isTutor || canTutorCompleteInitialProfile;
  const canEditPhoto = !isTutor || !isApprovedTutorProfile || isApprovedTutorEditMode;
  const isStudent = me?.role === "student";
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
    () => buildSelectOptions(availableCities, state ? "Select City" : "Select State first"),
    [availableCities, state]
  );
  const genderOptions = useMemo(
    () => [
      { value: "", label: "Select Gender" },
      { value: "male", label: "Male" },
      { value: "female", label: "Female" },
    ],
    []
  );
  const languageOptions = useMemo(
    () =>
      buildSelectOptions(
        WORLD_LANGUAGES.filter((language) => !selectedLanguages.includes(language)),
        selectedLanguages.length === WORLD_LANGUAGES.length ? "All listed languages selected" : "Select Language",
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
      return;
    }
    setMe(res.data);
    setFullName(res.data.fullName || "");
    setDisplayName(res.data.displayName);
    setMobileNumber(res.data.mobileNumber || "");
    setDob(res.data.dateOfBirth || "");
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

    if (res.data.role === "tutor") {
      const resTutor = await api.get<TutorData>("/api/tutors/me/verification");
      const verificationData = resTutor.ok ? resTutor.data : null;
      if (resTutor.ok) {
        setTutorData(resTutor.data);
        setFullName(resTutor.data.fullName || res.data.fullName || "");
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
  }, [showNotification]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (!isTutor || !tutorProfile || isApprovedTutorProfile) return;
    router.replace("/dashboard/verification");
  }, [isApprovedTutorProfile, isTutor, router, tutorProfile]);

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

    // Validate mandatory fields for students
    if (me.role === "student") {
      if (!me.profilePhotoUrl && !pendingPhotoUrl) {
        showNotification("error", "Profile photo is required");
        setIsLoading(false);
        return;
      }
      if (!dob.trim()) {
        showNotification("error", "Date of birth is required");
        setIsLoading(false);
        return;
      }
      if (!mobileNumber.trim()) {
        showNotification("error", "Mobile number is required");
        setIsLoading(false);
        return;
      }
      const studentMobileNumberError = getMobileNumberError(mobileNumber);
      if (studentMobileNumberError) {
        showNotification("error", studentMobileNumberError);
        setIsLoading(false);
        return;
      }
      if (!state.trim()) {
        showNotification("error", "State is required");
        setIsLoading(false);
        return;
      }
      if (!city.trim()) {
        showNotification("error", "City is required");
        setIsLoading(false);
        return;
      }
      if (!address.trim()) {
        showNotification("error", "Address is required");
        setIsLoading(false);
        return;
      }
    }

    // For students, use verification workflow
    if (me.role === "student") {
      const verificationData = {
        profilePhotoUrl: pendingPhotoUrl || me.profilePhotoUrl,
        dateOfBirth: dob,
        mobileNumber: sanitizeMobileNumberInput(mobileNumber),
        state: state,
        city: city,
        address: address,
      };

      const verificationRes = await api.post("/api/students/verification", verificationData);
      if (!verificationRes.ok) {
        showNotification("error", verificationRes.error || "Failed to submit verification request");
        setIsLoading(false);
        return;
      }

      // Clear pending changes
      setPendingPhotoUrl(null);
      setHasChanges(false);
      setIsLoading(false);

      showNotification("success", "Changes saved successfully!");

      // Reload profile to get updated data
      await load();
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

      if (canEditTutorPublicProfileFields && !hasSubmittedGender) {
        tutorSaveData.gender = gender;
      }
      if (canEditStateOfOrigin) {
        tutorSaveData.stateOfOrigin = stateOfOrigin;
        tutorSaveData.lgaOfOrigin = lgaOfOrigin;
      }

      // Include photo URL if there's a pending change
      if (pendingPhotoUrl && canEditPhoto && !isApprovedTutorEditMode) {
        tutorSaveData.profilePhotoUrl = pendingPhotoUrl;
      }

      const tutorRes = await api.put<TutorProfileResponse>("/api/tutors/me/profile", tutorSaveData);
      if (!tutorRes.ok) {
        showNotification("error", tutorRes.error || "Failed to save tutor profile");
        setIsLoading(false);
        return;
      }
      setTutorProfile(tutorRes.data);
    }

    // Clear pending changes and reload
    setPendingPhotoUrl(null);
    setHasChanges(false);
    setIsLoading(false);

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
      : me?.profilePhotoUrl
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
              {isLoading ? "Saving..." : "Save Changes"}
            </Button>
          </div>
        </div>
      </div>

      {isTutor && !isApprovedTutorProfile ? (
        <div className="rounded-2xl border border-info-border bg-info-soft p-4 text-[14px] leading-[22px] text-info-foreground">
          Verification approval is required before you can edit your tutor profile. Redirecting you to the verification page.
        </div>
      ) : null}

      {isTutor && isApprovedTutorProfile && !hasCompletedTutorProfile ? (
        <div className="rounded-2xl border border-green-200 bg-green-50 p-4 text-[14px] leading-[22px] text-green-900">
          Your verification has been approved. Complete your tutor profile once to publish it to students.
        </div>
      ) : null}

      {isTutor && isApprovedTutorProfile && hasCompletedTutorProfile && !isApprovedTutorEditMode ? (
        <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4 text-[14px] leading-[22px] text-amber-900">
          To update profile → Go to settings and make the neccessary changes.
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
                <img
                  key={currentPhotoUrl}
                  className="h-32 w-32 rounded-full border-4 border-white shadow-lg object-cover"
                  src={resolveMediaUrl(currentPhotoUrl)}
                  alt="Profile photo"
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
              <p className="mb-3 text-[14px] text-black/65">
                Upload photo.
              </p>
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                onChange={handleImageUpload}
                className="hidden"
                disabled={!canEditPhoto}
              />
              <Button
                variant="secondary"
                onClick={triggerFileInput}
                disabled={uploadingImage || !canEditPhoto}
              >
                {!canEditPhoto ? "change via settings" : uploadingImage ? "uploading..." : "Change Photo"}
              </Button>
            </div>
          </div>
        </div>
      )}

      <div className="form-panel rounded-2xl p-4">
        <div className="mb-6 grid gap-4 md:grid-cols-2">
          <div className="md:col-span-2">
            <h2 className="mb-3 text-[18px] font-semibold">Basic Information</h2>
          </div>
          <Input
            label="Full Name"
            value={fullName}
            onChange={(e) => {
              setFullName(e.target.value);
              setHasChanges(true);
            }}
            disabled={isTutor ? !canEditLockedTutorIdentityFields : false}
            helperText={isApprovedListedTutor ? "" : undefined}
          />

          <Input
            label="Display Name"
            value={displayName}
            onChange={(e) => {
              setDisplayName(e.target.value);
              setHasChanges(true);
            }}
            disabled={!canEditVerificationBackedTutorFields}
            helperText={isApprovedTutorEditMode ? "You can still update your public display name." : undefined}
          />

          {isStudent ? (
            <Select
              label="State"
              labelClassName="text-sm"
              value={state}
              onChange={(e) => handleStudentStateChange(e.target.value)}
              options={stateOptions}
              disabled={!canEditVerificationBackedTutorFields}
            />
          ) : (
            <Select
              label="Home State"
              labelClassName="text-sm"
              value={state}
              onChange={(e) => {
                setState(e.target.value);
                setHasChanges(true);
              }}
              options={stateOptions}
              disabled={!canEditVerificationBackedTutorFields}
            />
          )}

          {isStudent ? (
            <Select
              label="City"
              labelClassName="text-sm"
              value={city}
              onChange={(e) => {
                setCity(e.target.value);
                setHasChanges(true);
              }}
              options={cityOptions}
              disabled={!canEditVerificationBackedTutorFields || !state}
            />
          ) : (
            <Input
              label="Home City"
              value={city}
              onChange={(e) => {
                setCity(e.target.value);
                setHasChanges(true);
              }}
              disabled={!canEditVerificationBackedTutorFields}
              placeholder="e.g. Lagos"
            />
          )}
        </div>

        <div className="mb-6 grid gap-4 md:grid-cols-2">
          <Input
            label={isTutor ? "Home Address" : "Address"}
            value={address}
            onChange={(e) => {
              setAddress(e.target.value);
              setHasChanges(true);
            }}
            disabled={!canEditVerificationBackedTutorFields}
            placeholder="Full address"
          />

          <Input
            label="Email Address"
            value={me?.email || ""}
            disabled
            helperText="Change securely in Settings with an email OTP."
          />
        </div>

        <div className="mb-6 grid gap-4 md:grid-cols-2">
          {isTutor ? (
            <Select
              label="State of Origin"
              labelClassName="text-sm"
              value={stateOfOrigin}
              onChange={(e) => {
                setStateOfOrigin(e.target.value);
                setHasChanges(true);
              }}
              options={stateOfOriginOptions}
              disabled={!canEditStateOfOrigin}
            />
          ) : null}

          {isTutor ? (
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
          ) : null}
        </div>

        <div className="mb-6 grid gap-4 md:grid-cols-3">
          <Input
            label="Mobile Number"
            value={mobileNumber}
            onChange={(e) => {
              setMobileNumber(sanitizeMobileNumberInput(e.target.value));
              setHasChanges(true);
            }}
            disabled
            placeholder="+2348012345678"
            helperText="Change securely in Settings with an email OTP."
          />

          {pendingMobileRequests.length > 0 && (
            // <div className="md:col-span-2">
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
            // </div>
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
            helperText={isApprovedListedTutor ? "" : ""}
          />

          <div className="grid gap-1">
            <Select
              label="Gender"
              labelClassName="text-sm"
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
                ? "Gender is locked after submission. Request a correction through Support; only an administrator can change it."
                : "Gender is locked after it is submitted."}
            </p>
            {hasSubmittedGender ? (
              <div className="mt-1">
                <Button variant="ghost" onClick={() => router.push("/dashboard/support")}>
                  Request Gender Correction
                </Button>
              </div>
            ) : null}
          </div>
        </div>

        <div className="mb-6 grid gap-4">
          {tutorData && (
            <div className="contents">
              <div className="md:col-span-2 mt-4 border-t border-border pt-4">
                <h2 className="mb-3 text-[18px] font-semibold">Verification Details</h2>
              </div>
              <div className="grid gap-4 md:col-span-2 md:grid-cols-3">
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
                  helperText={isApprovedListedTutor ? "" : "NIN must be exactly 11 digits."}
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
                  helperText={isApprovedListedTutor ? "" : "BVN must be exactly 11 digits."}
                  error={bvnNumberError ?? undefined}
                  required
                />

                <Input
                  label="Qualification"
                  value={qualification}
                  onChange={(e) => {
                    setQualification(e.target.value);
                    setHasChanges(true);
                  }}
                  disabled
                  helperText="Change securely in Settings with an email OTP."
                />
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
                  labelClassName="text-sm"
                  value={bio}
                  onChange={(e) => {
                    setBio(e.target.value);
                    setHasChanges(true);
                  }}
                  disabled={!canEditTutorPublicProfileFields}
                  placeholder="Share your experience, teaching style, and what students can expect."
                />
              </div>
              <div className="relative" ref={subjectPickerRef}>
                <label className="mb-2 block text-sm font-medium text-foreground">Subjects</label>
                <div className={`rounded-xl border p-2 transition ${canEditTutorPublicProfileFields
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
                <div className={`rounded-xl border p-2 transition ${canEditTutorPublicProfileFields
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

              {/* <Select
              label="Gender"
              value={gender}
              onChange={(e) => {
                setGender(e.target.value);
                setHasChanges(true);
              }}
              options={genderOptions}
              disabled={!canEditTutorPublicProfileFields}
            /> */}
              <label className={`md:col-span-2 inline-flex items-start gap-3 rounded-xl border px-3 py-3 text-[14px] leading-[22px] ${!canEditTutorPublicProfileFields ? "border-slate-200 bg-slate-100 text-slate-500" : "border-black/12 bg-white"
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
              <div className="md:col-span-2 rounded-xl border border-border bg-white p-4">
                <div className="text-[14px] font-semibold leading-[22px]">Teaching Methods</div>
                <p className="mt-1 text-[12px] leading-[18px] text-black/55">
                  Choose how you can teach students. Face-to-face is enabled by default.
                </p>
                <div className="mt-3 grid gap-3 md:grid-cols-2">
                  <label className={`inline-flex items-start gap-3 rounded-xl border px-3 py-3 text-[14px] leading-[22px] ${!canEditTutorPublicProfileFields ? "border-slate-200 bg-slate-100 text-slate-500" : "border-black/12 bg-white"
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
                  <label className={`inline-flex items-start gap-3 rounded-xl border px-3 py-3 text-[14px] leading-[22px] ${!canEditTutorPublicProfileFields ? "border-slate-200 bg-slate-100 text-slate-500" : "border-black/12 bg-white"
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
                <div className="text-[18px] leading-[18px] text-green-700">
                  Status: {tutorProfile?.verificationStatus ? tutorProfile.verificationStatus : "—"}
                </div>
                <div className="text-[12px] leading-[18px] text-black/55">
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
