"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "../shared/Button";
import { Input } from "../shared/Input";
import { RequireAuth } from "../shared/RequireAuth";
import { Select } from "../shared/Select";
import { api } from "../shared/api";
import { useAuthStore } from "../shared/authStore";
import { useFormDraft } from "../shared/useFormDraft";
import { getBvnNumberError, getMobileNumberError, getNinNumberError, sanitizeBvnInput, sanitizeMobileNumberInput, sanitizeNinInput } from "../shared/profileValidation";
import { WORLD_COUNTRIES } from "@/data/countries";
import {
  NIGERIA_STATE_LGAS,
  NIGERIA_STATES,
  NIGERIAN_TERTIARY_QUALIFICATIONS,
} from "../shared/nigeriaData";

type VerificationResponse = {
  status: string;
  notes: string | null;
  submittedAt: string | null;
  decidedAt: string | null;
  fullName?: string;
  firstName?: string;
  middleName?: string;
  lastName?: string;
  email?: string;
  mobileNumber?: string;
  dateOfBirth?: string | null;
  countryOfBirth?: string;
  nationality?: string;
  stateOfOrigin?: string;
  lgaOfOrigin?: string;
  profilePhotoUrl?: string;
  homeState?: string;
  homeCity?: string;
  homeAddress?: string;
  qualification?: string;
  ninNumber?: string;
  bvnNumber?: string;
  languages?: string[];
  documentUrls?: string[];
};

type MeResponse = {
  id: string;
  email: string;
  displayName?: string;
  fullName: string;
  mobileNumber: string;
  dateOfBirth: string | null;
  state?: string;
  city?: string;
  location?: string;
  address?: string;
  firstName?: string;
  middleName?: string;
  lastName?: string;
};

function buildSelectOptions(items: string[], placeholder: string, currentValue?: string) {
  const normalizedItems =
    currentValue && currentValue.trim() && !items.includes(currentValue)
      ? [currentValue, ...items]
      : items;

  return [
    { value: "", label: placeholder },
    ...normalizedItems.map((item) => ({ value: item, label: item })),
  ];
}

function splitStoredList(value?: string | null) {
  return (value ?? "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
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

function composeFullName(firstName: string, middleName: string, lastName: string) {
  return [firstName, middleName, lastName].map((value) => value.trim()).filter(Boolean).join(" ");
}

export default function DashboardVerificationPage({ accountRole = "tutor" }: { accountRole?: "student" | "tutor" }) {
  const router = useRouter();
  const isStudent = accountRole === "student";
  const verificationEndpoint = isStudent ? "/api/students/verification" : "/api/tutors/me/verification";
  const [state, setState] = useState<VerificationResponse | null>(null);
  const [me, setMe] = useState<MeResponse | null>(null);
  const accessToken = useAuthStore((s) => s.accessToken);
  const userId = useAuthStore((s) => s.userId);

  // Form State
  const [homeState, setHomeState] = useState("");
  const [homeCity, setHomeCity] = useState("");
  const [homeAddress, setHomeAddress] = useState("");
  const [selectedQualifications, setSelectedQualifications] = useState<string[]>([]);
  const [qualificationToAdd, setQualificationToAdd] = useState("");
  const [ninNumber, setNinNumber] = useState("");
  const [bvnNumber, setBvnNumber] = useState("");
  const [note, setNote] = useState("");
  const [dob, setDob] = useState("");
  const [profilePhoto, setProfilePhoto] = useState<File | null>(null);
  const [idDocument, setIdDocument] = useState<File | null>(null);
  const [qualificationDocument, setQualificationDocument] = useState<File | null>(null);
  const [firstName, setFirstName] = useState("");
  const [middleName, setMiddleName] = useState("");
  const [lastName, setLastName] = useState("");
  const [email, setEmail] = useState("");
  const [mobileNumber, setMobileNumber] = useState("");
  const [countryOfBirth, setCountryOfBirth] = useState("");
  const [nationality, setNationality] = useState("");
  const [stateOfOrigin, setStateOfOrigin] = useState("");
  const [lgaOfOrigin, setLgaOfOrigin] = useState("");
  const [hasAttemptedSubmit, setHasAttemptedSubmit] = useState(false);
  const [isFormReady, setIsFormReady] = useState(false);

  const [error, setError] = useState<string | null>(null);
  const [notification, setNotification] = useState<{ type: "success" | "error", message: string } | null>(null);

  const profilePhotoRef = useRef<HTMLInputElement>(null);
  const idDocumentRef = useRef<HTMLInputElement>(null);
  const qualificationDocumentRef = useRef<HTMLInputElement>(null);
  const clearDraft = useFormDraft(
    userId ? `prepvilla.form-draft.${userId}.verification.${accountRole}` : null,
    {
      homeState,
      homeCity,
      homeAddress,
      selectedQualifications,
      ninNumber,
      bvnNumber,
      dob,
      firstName,
      middleName,
      lastName,
      mobileNumber,
      countryOfBirth,
      nationality,
      stateOfOrigin,
      lgaOfOrigin,
    },
    (draft) => {
      if (typeof draft.homeState === "string") setHomeState(draft.homeState);
      if (typeof draft.homeCity === "string") setHomeCity(draft.homeCity);
      if (typeof draft.homeAddress === "string") setHomeAddress(draft.homeAddress);
      if (Array.isArray(draft.selectedQualifications)) {
        setSelectedQualifications(draft.selectedQualifications.filter((item): item is string => typeof item === "string"));
      }
      if (typeof draft.ninNumber === "string") setNinNumber(draft.ninNumber);
      if (typeof draft.bvnNumber === "string") setBvnNumber(draft.bvnNumber);
      if (typeof draft.dob === "string") setDob(draft.dob);
      if (typeof draft.firstName === "string") setFirstName(draft.firstName);
      if (typeof draft.middleName === "string") setMiddleName(draft.middleName);
      if (typeof draft.lastName === "string") setLastName(draft.lastName);
      if (typeof draft.mobileNumber === "string") setMobileNumber(draft.mobileNumber);
      if (typeof draft.countryOfBirth === "string") setCountryOfBirth(draft.countryOfBirth);
      if (typeof draft.nationality === "string") setNationality(draft.nationality);
      if (typeof draft.stateOfOrigin === "string") setStateOfOrigin(draft.stateOfOrigin);
      if (typeof draft.lgaOfOrigin === "string") setLgaOfOrigin(draft.lgaOfOrigin);
    },
    isFormReady,
  );

  const isApproved = state?.status === "approved";
  const isRejected = state?.status === "rejected";
  const qualificationOptions = buildSelectOptions(
    NIGERIAN_TERTIARY_QUALIFICATIONS.filter(
      (qualification) => !selectedQualifications.includes(qualification),
    ),
    selectedQualifications.length === NIGERIAN_TERTIARY_QUALIFICATIONS.length
      ? "All listed qualifications selected"
      : "Select Qualification",
    qualificationToAdd,
  );
  const stateOptions = buildSelectOptions(NIGERIA_STATES, "Select State", homeState);
  const stateOfOriginOptions = buildSelectOptions(NIGERIA_STATES, "Select State", stateOfOrigin);
  const countryOfBirthOptions = buildSelectOptions([...WORLD_COUNTRIES], "Select Country", countryOfBirth);
  const nationalityOptions = buildSelectOptions([...WORLD_COUNTRIES], "Select Nationality", nationality);
  const isNigeriaCountryOfBirth = ["nigeria", "nigerian"].includes(countryOfBirth.trim().toLowerCase());
  const lgaOfOriginOptions = buildSelectOptions(
    isNigeriaCountryOfBirth ? NIGERIA_STATE_LGAS[stateOfOrigin] ?? [] : [],
    stateOfOrigin ? "Select LGA" : "Select State First",
    lgaOfOrigin,
  );

  useEffect(() => {
    if (!isApproved || !me?.id) return;
    if (typeof window === "undefined") return;
    const key = `prepvilla.verification.redirected.${me.id}`;
    if (window.localStorage.getItem(key) === "1") return;
    const t = setTimeout(() => {
      window.localStorage.setItem(key, "1");
      router.push("/dashboard/profile");
    }, 2500);
    return () => clearTimeout(t);
  }, [isApproved, me?.id, router]);

  // Check if all mandatory fields are filled
  const hasProfilePhoto = Boolean(profilePhoto || state?.profilePhotoUrl);
  const hasIdDocument = Boolean(idDocument || state?.documentUrls?.[0]);
  const hasQualificationDocument = Boolean(qualificationDocument || state?.documentUrls?.[1]);
  const mobileNumberError = mobileNumber.trim() ? getMobileNumberError(mobileNumber) : null;
  const ninNumberError = ninNumber.trim() ? getNinNumberError(ninNumber) : null;
  const bvnNumberError = getBvnNumberError(bvnNumber, {
    required: !isStudent && hasAttemptedSubmit,
  });
  const hasCompleteVerificationInfo = Boolean(
    homeState.trim() &&
    homeCity.trim() &&
    homeAddress.trim() &&
    selectedQualifications.length > 0 &&
    ninNumber.trim() &&
    !ninNumberError &&
    (isStudent || bvnNumber.trim()) &&
    !bvnNumberError &&
    dob.trim() &&
    firstName.trim() &&
    lastName.trim() &&
    countryOfBirth.trim() &&
    nationality.trim() &&
    stateOfOrigin.trim() &&
    lgaOfOrigin.trim() &&
    mobileNumber.trim() &&
    !mobileNumberError &&
    hasProfilePhoto &&
    hasIdDocument &&
    hasQualificationDocument,
  );
  function addQualification(qualification: string) {
    if (!qualification || selectedQualifications.includes(qualification)) return;
    setSelectedQualifications((prev) => [...prev, qualification]);
    setQualificationToAdd("");
  }

  function removeQualification(qualification: string) {
    setSelectedQualifications((prev) => prev.filter((item) => item !== qualification));
  }

  function changeCountryOfBirth(value: string) {
    if (value !== countryOfBirth) {
      setStateOfOrigin("");
      setLgaOfOrigin("");
    }
    setCountryOfBirth(value);
  }

  function changeStateOfOrigin(value: string) {
    if (value !== stateOfOrigin) setLgaOfOrigin("");
    setStateOfOrigin(value);
  }

  async function uploadFile(file: File, kind: "photo" | "id_document" | "qualification_document") {
    const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8500";
    const form = new FormData();
    form.append("file", file);
    form.append("kind", kind);
    const loc = composeFullName(firstName, middleName, lastName).replace(/\s+/g, "_") || "verification";
    form.append("location", loc);
    const res = await fetch(`${baseUrl}/api/uploads`, {
      method: "POST",
      headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : undefined,
      body: form,
    });
    const body = (await res.json()) as { url?: string; detail?: string };
    if (!res.ok || !body.url) {
      throw new Error(body.detail ?? `Upload failed (${res.status})`);
    }
    return body.url;
  }

  const load = useCallback(async () => {
    setError(null);
    setNotification(null);
    const [resMe, resVer] = await Promise.all([
      api.get<MeResponse>("/api/me"),
      api.get<VerificationResponse>(verificationEndpoint),
    ]);
    const meData = resMe.ok ? resMe.data : null;

    if (meData) {
      const names = meData.firstName || meData.lastName
        ? {
          firstName: meData.firstName || "",
          middleName: meData.middleName || "",
          lastName: meData.lastName || "",
        }
        : splitFullName(meData.fullName || meData.displayName || "");
      setMe(meData);
      if (meData.dateOfBirth) setDob(meData.dateOfBirth);
      setFirstName(names.firstName);
      setMiddleName(names.middleName);
      setLastName(names.lastName);
      setEmail(meData.email || "");
      setMobileNumber(meData.mobileNumber || "");
      setHomeState(meData.state || "");
      setHomeCity(meData.city || meData.location || "");
      setHomeAddress(meData.address || "");
    }

    if (resVer.ok) {
      const names = resVer.data.firstName || resVer.data.lastName
        ? {
          firstName: resVer.data.firstName || "",
          middleName: resVer.data.middleName || "",
          lastName: resVer.data.lastName || "",
        }
        : splitFullName(resVer.data.fullName || meData?.fullName || meData?.displayName || "");
      setState(resVer.data);
      setFirstName(names.firstName);
      setMiddleName(names.middleName);
      setLastName(names.lastName);
      setEmail(resVer.data.email || meData?.email || "");
      setMobileNumber(resVer.data.mobileNumber || meData?.mobileNumber || "");
      setDob(resVer.data.dateOfBirth || meData?.dateOfBirth || "");
      setCountryOfBirth(resVer.data.countryOfBirth || "");
      setNationality(resVer.data.nationality || "");
      setStateOfOrigin(resVer.data.stateOfOrigin || "");
      setLgaOfOrigin(resVer.data.lgaOfOrigin || "");
      setHomeState(resVer.data.homeState || meData?.state || "");
      setHomeCity(resVer.data.homeCity || meData?.city || meData?.location || "");
      setHomeAddress(resVer.data.homeAddress || meData?.address || "");
      setSelectedQualifications(splitStoredList(resVer.data.qualification));
      setNinNumber(resVer.data.ninNumber || "");
      setBvnNumber(resVer.data.bvnNumber || "");
    }
    setIsFormReady(true);
  }, [verificationEndpoint]);

  useEffect(() => {
    void load();
  }, [load]);

  async function submit() {
    setHasAttemptedSubmit(true);
    setError(null);
    const fullName = composeFullName(firstName, middleName, lastName);
    const normalizedMobileNumber = sanitizeMobileNumberInput(mobileNumber);
    const normalizedNinNumber = sanitizeNinInput(ninNumber);
    const normalizedBvnNumber = sanitizeBvnInput(bvnNumber);
    const nextMobileNumberError = getMobileNumberError(normalizedMobileNumber);
    const nextNinNumberError = getNinNumberError(normalizedNinNumber);
    const nextBvnNumberError = getBvnNumberError(normalizedBvnNumber, { required: !isStudent });
    if (nextMobileNumberError) {
      setError(nextMobileNumberError);
      return;
    }
    if (nextNinNumberError) {
      setError(nextNinNumberError);
      return;
    }
    if (nextBvnNumberError) {
      setError(nextBvnNumberError);
      return;
    }
    if (!hasCompleteVerificationInfo) {
      setError("Please complete all required fields before submitting.");
      return;
    }

    let profilePhotoUrl = state?.profilePhotoUrl || "";
    const nextDocumentUrls = [...(state?.documentUrls || [])];

    try {
      if (profilePhoto) {
        profilePhotoUrl = await uploadFile(profilePhoto, "photo");
      }
      if (!profilePhotoUrl) {
        throw new Error("Please upload a profile photo.");
      }

      if (idDocument) {
        nextDocumentUrls[0] = await uploadFile(idDocument, "id_document");
      }
      if (qualificationDocument) {
        nextDocumentUrls[1] = await uploadFile(qualificationDocument, "qualification_document");
      }
      if (!nextDocumentUrls[0] || !nextDocumentUrls[1]) {
        throw new Error("Please upload both your ID document and qualification document.");
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed");
      return;
    }

    const res = await api.post<VerificationResponse>(verificationEndpoint, {
      homeState,
      homeCity,
      homeAddress,
      qualification: selectedQualifications.join(", "),
      firstName,
      middleName,
      lastName,
      email,
      fullName,
      countryOfBirth,
      nationality,
      stateOfOrigin,
      lgaOfOrigin,
      ninNumber: normalizedNinNumber,
      bvnNumber: normalizedBvnNumber || "",
      dateOfBirth: dob,
      profilePhotoUrl,
      documentUrls: nextDocumentUrls,
      notes: note,
      mobileNumber: normalizedMobileNumber,
    });
    if (!res.ok) {
      setError(res.error);
      return;
    }

    clearDraft();
    setState(res.data);
    setProfilePhoto(null);
    setIdDocument(null);
    setQualificationDocument(null);
    setNote("");
    setNotification({
      type: "success",
      message: isStudent
        ? "Verification completed successfully. You can now contact tutors and book lessons."
        : "Verification completed successfully. Your identity details have been verified.",
    });
    await load();
  }

  return (
    <RequireAuth allow={[accountRole]}>
      <div className="mb-2 grid gap-4">
        <div className="mb-2 form-panel rounded-xl p-4">
          <div className="flex items-center justify-between gap-3">
            <div>
              <h1 className="brand-heading text-[20px] font-semibold leading-[28px]">Verification</h1>
              <p className="mt-1 text-xs leading-[20px] text-black/65">Submit your identity details and track verification status.</p>
            </div>
            <Button variant="secondary" onClick={load}>Refresh</Button>
          </div>
        </div>

        {error ? <div className="text-xs leading-[20px] text-danger">{error}</div> : null}

        {notification && (
          <div className={`rounded-xl p-4 text-[14px] leading-[22px] ${notification.type === "success"
            ? "bg-green-50 border border-green-200 text-green-800"
            : "bg-red-50 border border-red-200 text-red-800"
            }`}>
            {notification.message}
          </div>
        )}

        <div className="mb-2 form-panel rounded-xl p-4">
          {/* Status Banner */}
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3 border-b border-border pb-4">
            <div>
              <div className="text-xs leading-[20px] text-black/55">Status</div>
              <div className={`text-[16px] font-semibold leading-[24px] ${isApproved ? "text-green-600" : isRejected ? "text-red-600" : "text-yellow-600"
                }`}>
                {state?.status === "approved" ? "✓ Approved" :
                  state?.status === "rejected" ? "✗ Rejected" :
                    state?.status === "pending" ? "Verification Incomplete" : "Not Submitted"}
              </div>
              {isApproved && (
                <div className="mt-2 text-xs leading-[20px] text-green-600">
                  Your verification is complete. Future logins will take you to your profile page.
                </div>
              )}
              {state?.status === "pending" ? (
                <div className="mt-2 text-xs leading-[20px] text-amber-700">
                  Resubmit your details to complete automated identity verification.
                </div>
              ) : null}
            </div>
          </div>
        </div>

        <div className="mb-2 form-panel rounded-xl p-4">
          <h3 className="brand-heading mb-1 mt-1 text-lg font-semibold">Bio-data</h3>
          <p className="mb-4 text-xs leading-[20px] text-black/55">
            {isStudent
              ? "Enter your personal details exactly as they appear on your NIN record and, if supplied, your BVN record."
              : "Enter your personal details exactly as they appear on your NIN and BVN records."}
          </p>

          <div className={`grid gap-4 md:grid-cols-3 ${isApproved ? "opacity-75" : ""}`}>
            <Input
              label="First name *"
              value={firstName}
              onChange={(e) => setFirstName(e.target.value)}
              disabled={isApproved}
              placeholder="First name"
              required
            />
            <Input
              label="Middle name"
              value={middleName}
              onChange={(e) => setMiddleName(e.target.value)}
              disabled={isApproved}
              placeholder="Middle name (optional)"
            />
            <Input
              label="Last name *"
              value={lastName}
              onChange={(e) => setLastName(e.target.value)}
              disabled={isApproved}
              placeholder="Last name"
              required
            />
          </div><br />

          <div className={`grid gap-4 md:grid-cols-3 ${isApproved ? "opacity-75" : ""}`}>
            <Input
              label="Email *"
              type="email"
              value={email}
              disabled
              helperText="Verified email"
              required
            />
            <Input
              label={isStudent ? "Mobile (Linked to NIN) *" : "Mobile (Linked to NIN / BVN) *"}
              value={mobileNumber}
              onChange={(e) => setMobileNumber(sanitizeMobileNumberInput(e.target.value))}
              disabled={isApproved}
              placeholder="+2348012345678"
              helperText="Start with +234 followed by 10 digits."
              error={mobileNumberError ?? undefined}
              required
            />
            <Input
              label="Date of Birth *"
              type="date"
              value={dob}
              onChange={(e) => setDob(e.target.value)}
              disabled={!!me?.dateOfBirth || isApproved}
              required
            />
          </div><br />

          <div className={`grid gap-4 md:grid-cols-2 ${isApproved ? "opacity-75" : ""}`}>
            <Select
              label="Country of Birth *"
              value={countryOfBirth}
              onChange={(e) => changeCountryOfBirth(e.target.value)}
              options={countryOfBirthOptions}
              disabled={isApproved}
              required
            />
            <Select
              label="Nationality *"
              value={nationality}
              onChange={(e) => setNationality(e.target.value)}
              options={nationalityOptions}
              disabled={isApproved}
              required
            />
            {isNigeriaCountryOfBirth ? (
              <Select
                label="State of Origin *"
                value={stateOfOrigin}
                onChange={(e) => changeStateOfOrigin(e.target.value)}
                options={stateOfOriginOptions}
                disabled={isApproved}
                required
              />
            ) : (
              <Input
                label="State / Region of Origin *"
                value={stateOfOrigin}
                onChange={(e) => setStateOfOrigin(e.target.value)}
                disabled={isApproved}
                placeholder="Enter your state or region"
                required
              />
            )}
            {isNigeriaCountryOfBirth ? (
              <Select
                label="LGA of Origin *"
                value={lgaOfOrigin}
                onChange={(e) => setLgaOfOrigin(e.target.value)}
                options={lgaOfOriginOptions}
                disabled={isApproved || !stateOfOrigin}
                required
              />
            ) : (
              <Input
                label="Local Government / Region *"
                value={lgaOfOrigin}
                onChange={(e) => setLgaOfOrigin(e.target.value)}
                disabled={isApproved}
                placeholder="Enter your local government or region"
                required
              />
            )}
          </div><br />

          <div className={`mb-10 grid gap-4 md:grid-cols-2 ${isApproved ? "opacity-75" : ""}`}>
            <Input
              label="NIN Number *"
              value={ninNumber}
              onChange={(e) => setNinNumber(sanitizeNinInput(e.target.value))}
              disabled={isApproved}
              inputMode="numeric"
              placeholder="12345678901"
              helperText="NIN must be exactly 11 digits."
              error={ninNumberError ?? undefined}
              required
            />
            <Input
              label="BVN Number *"
              value={bvnNumber}
              onChange={(e) => setBvnNumber(sanitizeBvnInput(e.target.value))}
              disabled={isApproved}
              inputMode="numeric"
              placeholder="12345678901"
              helperText={isStudent ? "Optional. If provided, BVN must be exactly 11 digits and will be verified." : "BVN must be exactly 11 digits."}
              error={bvnNumberError ?? undefined}
              required={!isStudent}
            />
          </div>
        </div>

        <div className="mb-2 form-panel rounded-xl p-4">
          <h3 className="brand-heading mb-1 text-lg font-semibold">Qualifications</h3>
          <p className="mb-4 text-xs leading-[20px] text-black/55">
            Select every qualification that applies and upload supporting evidence below.
          </p>
          <Select
            label="Highest Qualification *"
            value={qualificationToAdd}
            onChange={(event) => addQualification(event.target.value)}
            options={qualificationOptions}
            disabled={isApproved || selectedQualifications.length === NIGERIAN_TERTIARY_QUALIFICATIONS.length}
            required={selectedQualifications.length === 0}
          />
          {selectedQualifications.length ? (
            <div className="mt-3 flex flex-wrap gap-2">
              {selectedQualifications.map((qualification) => (
                <span key={qualification} className="inline-flex items-center gap-2 rounded-full bg-primary-soft px-3 py-1.5 text-xs font-semibold text-primary-deep">
                  {qualification}
                  {!isApproved ? (
                    <button
                      type="button"
                      onClick={() => removeQualification(qualification)}
                      className="text-black/45 transition hover:text-danger"
                      aria-label={`Remove ${qualification}`}
                    >
                      ×
                    </button>
                  ) : null}
                </span>
              ))}
            </div>
          ) : null}
        </div>

        <div className="mb-2">
          <div className="form-inset md:col-span-2 rounded-xl p-4">
            <div className="mb-4">
              <h4 className="text-[20px] font-semibold leading-[24px] text-black">Residence</h4>
              <p className="text-xs leading-[20px] text-black/55">
                Provide your current residential details exactly as they appear on your documents.
              </p>
            </div>
            <div className="mb-4 grid gap-4 md:grid-cols-2">
              <Input
                label="Country *"
                value={countryOfBirth}
                onChange={(e) => setCountryOfBirth(e.target.value)}
                disabled={isApproved}
                placeholder="e.g. Nigeria"
                required
              />
              <Select
                label="State *"
                value={homeState}
                onChange={(e) => setHomeState(e.target.value)}
                options={stateOptions}
                disabled={isApproved}
                required
              />
            </div>
            <div className="grid gap-4 md:grid-cols-2">
              <Input
                label="City *"
                value={homeCity}
                onChange={(e) => setHomeCity(e.target.value)}
                disabled={isApproved}
                placeholder="e.g. Lagos"
                required
              />

              <Input
                label="Address *"
                value={homeAddress}
                onChange={(e) => setHomeAddress(e.target.value)}
                disabled={isApproved}
                placeholder="Full residential address"
                required
              />
            </div>
          </div>
        </div>

        <div className="mb-2">
          <div className="mb-2 md:col-span-2">
            <div className="grid gap-4 md:grid-cols-3">
              <div className="form-inset grid gap-2 rounded-xl p-3">
                <span className="text-xs leading-[20px] text-black/55">
                  Profile Photo {isApproved && "(Locked after approval)"}
                </span>
                <input
                  ref={profilePhotoRef}
                  type="file"
                  accept="image/*"
                  onChange={(e) => setProfilePhoto(e.target.files?.[0] ?? null)}
                  style={{ display: "none" }}
                  disabled={isApproved}
                />
                <Button variant="secondary" onClick={() => profilePhotoRef.current?.click()} disabled={isApproved}>
                  Choose File
                </Button>
                <span className="min-h-5 text-xs text-black/55">
                  {profilePhoto ? profilePhoto.name : state?.profilePhotoUrl ? "Saved profile photo on file" : "No file selected"}
                </span>
              </div>
              <div className="form-inset grid gap-2 rounded-xl p-3">
                <span className="text-xs leading-[20px] text-black/55">
                  ID Document (NIN/Passport) {isApproved && "(Contact support to change)"}
                </span>
                <input
                  ref={idDocumentRef}
                  type="file"
                  accept="image/*,application/pdf"
                  onChange={(e) => setIdDocument(e.target.files?.[0] ?? null)}
                  style={{ display: "none" }}
                  disabled={isApproved}
                />
                <Button variant="secondary" onClick={() => idDocumentRef.current?.click()} disabled={isApproved}>
                  Choose File
                </Button>
                <span className="min-h-5 text-xs text-black/55">
                  {idDocument ? idDocument.name : state?.documentUrls?.[0] ? "Saved ID document on file" : "No file selected"}
                </span>
              </div>
              <div className="form-inset grid gap-2 rounded-xl p-3">
                <span className="text-xs leading-[20px] text-black/55">
                  Qualification Document {isApproved && "(Contact support to change)"}
                </span>
                <input
                  ref={qualificationDocumentRef}
                  type="file"
                  accept="image/*,application/pdf"
                  onChange={(e) => setQualificationDocument(e.target.files?.[0] ?? null)}
                  style={{ display: "none" }}
                  disabled={isApproved}
                />
                <Button variant="secondary" onClick={() => qualificationDocumentRef.current?.click()} disabled={isApproved}>
                  Choose File
                </Button>
                <span className="min-h-5 text-xs text-black/55">
                  {qualificationDocument ? qualificationDocument.name : state?.documentUrls?.[1] ? "Saved qualification document on file" : "No file selected"}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="mb-2 form-panel rounded-xl p-4">
        {/* Submit Button - Always shown, disabled based on approval and changes */}
        <div className="mt-6">
          <Button
            onClick={() => void submit()}
            disabled={isApproved}
          >
            {isApproved ? "Verification Complete" : "Submit Verification"}
          </Button>
          {isApproved && (
            <div className="mt-4 p-3 bg-green-50 border border-green-200 rounded-lg text-green-700 text-sm">
              {isStudent
                ? "✓ Verification Complete - You can contact tutors and book lessons"
                : "✓ Verification Complete - Your profile is listed and visible to students"}
            </div>
          )}
        </div>
        {/* Mandatory Fields Notice */}
        {!isApproved && (
          <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
            <p className="text-xs text-yellow-700">
              <strong>* All fields marked with asterisk are mandatory.</strong><br />
              Please ensure all documents are clear and readable. Incomplete submissions will delay verification.
            </p>
          </div>
        )}
      </div>
    </RequireAuth >
  );
}
