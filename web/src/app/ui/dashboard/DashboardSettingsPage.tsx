"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Key, Mail, Phone, Shield, UserX } from "lucide-react";
import { Button } from "../shared/Button";
import { Input } from "../shared/Input";
import { OtpResendButton } from "../shared/OtpResendButton";
import { api } from "../shared/api";
import { useAuthStore } from "../shared/authStore";
import { getMobileNumberError, sanitizeMobileNumberInput } from "../shared/profileValidation";

type MeResponse = {
  isFrozen: boolean;
  freezeUntil: string | null;
};

type TutorSettingsProfile = {
  verificationStatus: string;
  isListed: boolean;
};

export default function DashboardSettingsPage() {
  const router = useRouter();
  const clear = useAuthStore((s) => s.clear);
  const role = useAuthStore((s) => s.role);

  const [me, setMe] = useState<MeResponse | null>(null);
  const [tutorProfile, setTutorProfile] = useState<TutorSettingsProfile | null>(null);
  const tutorVerificationStatus = (tutorProfile?.verificationStatus || "").toLowerCase();
  const isApprovedTutor = tutorVerificationStatus === "approved" || tutorVerificationStatus === "verified";
  const hasCompletedTutorProfile = Boolean(tutorProfile?.isListed);
  const isApprovedListedTutor = role === "tutor" && isApprovedTutor && hasCompletedTutorProfile;

  // Password change
  const [passwordStep, setPasswordStep] = useState(0);
  const [newPassword, setNewPassword] = useState("");
  const [confirmNewPassword, setConfirmNewPassword] = useState("");
  const [otp, setOtp] = useState("");

  // Email change
  const [emailStep, setEmailStep] = useState(0);
  const [newEmail, setNewEmail] = useState("");

  // Phone change
  const [phoneStep, setPhoneStep] = useState(0);
  const [newPhone, setNewPhone] = useState("");
  const newPhoneError = newPhone.trim() ? getMobileNumberError(newPhone) : null;

  // Freeze
  const [freezeStep, setFreezeStep] = useState(0);
  const [freezeStartsOn, setFreezeStartsOn] = useState("");
  const [freezeEndsOn, setFreezeEndsOn] = useState("");

  // Delete
  const [deleteStep, setDeleteStep] = useState(0);

  async function loadMe() {
    const res = await api.get<MeResponse>("/api/me");
    if (!res.ok) return;
    setMe({ isFrozen: res.data.isFrozen, freezeUntil: res.data.freezeUntil });
  }

  const loadTutorProfile = useCallback(async () => {
    if (role !== "tutor") return;
    const res = await api.get<TutorSettingsProfile>("/api/tutors/me/profile");
    if (!res.ok) return;
    setTutorProfile(res.data);
  }, [role]);

  useEffect(() => {
    void loadMe();
  }, []);

  useEffect(() => {
    void loadTutorProfile();
  }, [loadTutorProfile]);

  async function requestPasswordOtp(): Promise<boolean> {
    if (newPassword !== confirmNewPassword) {
      alert("Passwords do not match");
      return false;
    }
    const res = await api.post<{ ok: boolean }>("/api/me/change-password/request", { newPassword });
    if (!res.ok) {
      alert(res.error);
      return false;
    }
    setOtp("");
    setPasswordStep(2);
    alert("OTP sent to your email");
    return true;
  }

  async function confirmPasswordChange() {
    const res = await api.post<{ ok: boolean }>("/api/me/change-password/confirm", { code: otp });
    if (!res.ok) {
      alert(res.error);
      return;
    }
    setOtp("");
    setNewPassword("");
    setConfirmNewPassword("");
    setPasswordStep(0);
    alert("Password changed");
  }

  async function requestEmailOtp(): Promise<boolean> {
    const res = await api.post<{ ok: boolean }>("/api/me/change-email/request", { newEmail });
    if (!res.ok) {
      alert(res.error);
      return false;
    }
    setOtp("");
    setEmailStep(2);
    alert("OTP sent to your email");
    return true;
  }

  async function confirmEmailChange() {
    const res = await api.post<{ ok: boolean }>("/api/me/change-email/confirm", { code: otp });
    if (!res.ok) {
      alert(res.error);
      return;
    }
    setOtp("");
    setNewEmail("");
    setEmailStep(0);
    alert("Email changed");
  }

  async function requestPhoneOtp(): Promise<boolean> {
    const phoneError = getMobileNumberError(newPhone);
    if (phoneError) {
      alert(phoneError);
      return false;
    }
    const res = await api.post<{ ok: boolean }>("/api/me/change-phone/request", { newPhone });
    if (!res.ok) {
      alert(res.error);
      return false;
    }
    setOtp("");
    setPhoneStep(2);
    alert("OTP sent to your email");
    return true;
  }

  async function confirmPhoneChange() {
    const res = await api.post<{ ok: boolean }>("/api/me/change-phone/confirm", { code: otp });
    if (!res.ok) {
      alert(res.error);
      return;
    }
    setOtp("");
    setNewPhone("");
    setPhoneStep(0);
    alert("Phone changed");
  }

  async function requestFreezeOtp(): Promise<boolean> {
    if (!freezeStartsOn || !freezeEndsOn) return false;
    const start = new Date(`${freezeStartsOn}T00:00:00`);
    const end = new Date(`${freezeEndsOn}T00:00:00`);
    const today = new Date();
    today.setHours(0, 0, 0, 0);

    if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())) {
      alert("Please pick valid dates");
      return false;
    }
    if (start < today) {
      alert("Start date must be today or later");
      return false;
    }
    if (end < start) {
      alert("End date must be after start date");
      return false;
    }
    const maxEnd = new Date(start);
    maxEnd.setMonth(maxEnd.getMonth() + 3);
    if (end > maxEnd) {
      alert("Freeze period cannot exceed 3 months");
      return false;
    }

    const res = await api.post<{ ok: boolean }>("/api/me/freeze-account/request", { startsOn: freezeStartsOn, endsOn: freezeEndsOn });
    if (!res.ok) {
      alert(res.error);
      return false;
    }
    setFreezeStep(2);
    alert("OTP sent to your email");
    return true;
  }

  async function confirmFreeze() {
    const res = await api.post<{ ok: boolean; isFrozen: boolean; freezeUntil: string }>("/api/me/freeze-account/confirm", { code: otp });
    if (!res.ok) {
      alert(res.error);
      return;
    }
    setOtp("");
    setFreezeStep(0);
    await loadMe();
  }

  async function unfreezeAccount() {
    const res = await api.post<{ ok: boolean; isFrozen: boolean }>("/api/me/unfreeze-account", {});
    if (!res.ok) {
      alert(res.error);
      return;
    }
    await loadMe();
  }

  async function deleteAccount() {
    const res = await api.post<{ ok: boolean }>("/api/me/delete-account", { confirm: true, code: otp });
    if (!res.ok) {
      alert(res.error);
      return;
    }
    clear();
    router.push("/");
  }

  async function requestDeleteOtp(): Promise<boolean> {
    const res = await api.post<{ ok: boolean }>("/api/me/delete-account/request", {});
    if (!res.ok) {
      alert(res.error);
      return false;
    }
    alert("OTP sent to your email");
    setDeleteStep(2);
    return true;
  }

  return (
    <div className="space-y-8">
      {/* Header Section */}
      <div className="rounded-2xl border border-black/10 bg-[linear-gradient(135deg,rgba(255,255,255,0.98)_0%,rgba(247,241,232,0.98)_58%,rgba(239,226,232,0.92)_100%)] p-8 shadow-[0_22px_44px_rgba(15,23,40,0.08)]">
        <div className="mb-4 flex items-center gap-4">
          <div className="rounded-full bg-[linear-gradient(135deg,var(--palette-navy-deep)_0%,var(--palette-coral)_100%)] p-3 text-white shadow-[0_18px_30px_rgba(15,23,40,0.18)]">
            <Shield className="h-8 w-8" />
          </div>
          <div>
            <h1 className="brand-heading text-[32px] font-bold leading-[40px]">Account Settings</h1>
            <p className="text-[16px] leading-[24px] text-black/65">Manage your account preferences and security settings</p>
          </div>
        </div>
      </div>

      {/* Security Settings */}
      <div className="space-y-6">
        {role === "tutor" ? (
          <div className="form-panel rounded-2xl p-6">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div>
                <h3 className="text-[18px] font-semibold mb-2">Edit Profile</h3>
                <p className="text-[14px] text-black/65">
                  {!isApprovedTutor
                    ? "Your tutor profile unlocks after verification is approved."
                    : hasCompletedTutorProfile
                      ? "Update editable information, speak to support for sensitive data."
                      : "Finish your tutor profile so it can be published to students."}
                </p>
              </div>
              <Button
                variant="secondary"
                onClick={() =>
                  router.push(
                    !isApprovedTutor
                      ? "/dashboard/verification"
                      : hasCompletedTutorProfile
                        ? "/dashboard/profile?edit=profile"
                        : "/dashboard/profile",
                  )
                }
              >
                {!isApprovedTutor ? "Open Verification" : hasCompletedTutorProfile ? "Update Profile" : "Complete Profile"}
              </Button>
            </div>
          </div>
        ) : null}

        <div className="text-[20px] font-semibold">Security</div>
        
        {/* Change Password */}
        <div className="form-panel rounded-2xl p-6">
          <div className="mb-6 flex items-start gap-4">
            <div className="rounded-full bg-black p-3 text-white">
              <Key className="h-6 w-6" />
            </div>
            <div className="flex-1">
              <h3 className="text-[18px] font-semibold mb-2">Change Password</h3>
              <p className="mb-4 text-[14px] text-black/65">Update your password to keep your account secure</p>
              
              {passwordStep === 0 && (
                <Button
                  variant="secondary"
                  onClick={() => {
                    setOtp("");
                    setNewPassword("");
                    setConfirmNewPassword("");
                    setPasswordStep(1);
                  }}
                >
                  Change Password
                </Button>
              )}
              {passwordStep === 1 && (
                <div className="space-y-4">
                  <Input 
                    label="New Password"
                    type="password"
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    placeholder="Enter your new password"
                  />
                  <Input
                    label="Confirm New Password"
                    type="password"
                    value={confirmNewPassword}
                    onChange={(e) => setConfirmNewPassword(e.target.value)}
                    placeholder="Re-enter your new password"
                  />
                  <div className="flex gap-3">
                    <Button
                      variant="secondary"
                      onClick={requestPasswordOtp}
                      disabled={newPassword.length < 6 || newPassword !== confirmNewPassword}
                    >
                      Send OTP
                    </Button>
                    <Button
                      variant="ghost"
                      onClick={() => {
                        setOtp("");
                        setNewPassword("");
                        setConfirmNewPassword("");
                        setPasswordStep(0);
                      }}
                    >
                      Cancel
                    </Button>
                  </div>
                </div>
              )}
              {passwordStep === 2 && (
                <div className="space-y-4">
                  <Input 
                    label="Enter OTP"
                    value={otp}
                    onChange={(e) => setOtp(e.target.value)}
                    placeholder="Enter the 6-character code"
                  />
                  <div className="flex gap-3">
                    <Button onClick={confirmPasswordChange}>
                      Update Password
                    </Button>
                    <OtpResendButton onResend={requestPasswordOtp} />
                    <Button
                      variant="ghost"
                      onClick={() => {
                        setOtp("");
                        setNewPassword("");
                        setConfirmNewPassword("");
                        setPasswordStep(0);
                      }}
                    >
                      Cancel
                    </Button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Change Email */}
        <div className="form-panel rounded-2xl p-6">
          <div className="mb-6 flex items-start gap-4">
            <div className="rounded-full bg-[var(--secondary-color-soft)] p-3">
              <Mail className="w-6 h-6 text-green-600" />
            </div>
            <div className="flex-1">
              <h3 className="text-[18px] font-semibold mb-2">Change Email Address</h3>
              <p className="mb-4 text-[14px] text-black/65">Update your email address for account notifications and recovery</p>
              {isApprovedListedTutor ? (
                <div className="mb-4 rounded-xl border border-slate-200 bg-slate-50 p-3 text-[13px] text-slate-700">
                  Approved tutor email changes are locked. Contact support instead.
                </div>
              ) : null}
              
              {!isApprovedListedTutor && emailStep === 0 && (
                <Button variant="secondary" onClick={() => { setOtp(""); setEmailStep(1); }}>
                  Change Email
                </Button>
              )}
              {!isApprovedListedTutor && emailStep === 1 && (
                <div className="space-y-4">
                  <Input 
                    label="New Email Address"
                    type="email"
                    value={newEmail}
                    onChange={(e) => setNewEmail(e.target.value)}
                    placeholder="Enter your new email address"
                  />
                  <div className="flex gap-3">
                    <Button variant="secondary" onClick={requestEmailOtp} disabled={!newEmail.trim()}>
                      Send OTP
                    </Button>
                    <Button variant="ghost" onClick={() => setEmailStep(0)}>
                      Cancel
                    </Button>
                  </div>
                </div>
              )}
              {!isApprovedListedTutor && emailStep === 2 && (
                <div className="space-y-4">
                  <Input 
                    label="Enter OTP"
                    value={otp}
                    onChange={(e) => setOtp(e.target.value)}
                    placeholder="Enter the 6-character code"
                  />
                  <div className="flex gap-3">
                    <Button onClick={confirmEmailChange}>
                      Update Email
                    </Button>
                    <OtpResendButton onResend={requestEmailOtp} />
                    <Button variant="ghost" onClick={() => setEmailStep(0)}>
                      Cancel
                    </Button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Change Phone */}
        <div className="form-panel rounded-2xl p-6">
          <div className="mb-6 flex items-start gap-4">
            <div className="rounded-full bg-[var(--primary-soft)] p-3">
              <Phone className="h-6 w-6 text-[color:var(--palette-coral-deep)]" />
            </div>
            <div className="flex-1">
              <h3 className="text-[18px] font-semibold mb-2">Change Phone Number</h3>
              <p className="mb-4 text-[14px] text-black/65">Update your phone number for SMS notifications and verification</p>
              {isApprovedListedTutor ? (
                <div className="mb-4 rounded-xl border border-slate-200 bg-slate-50 p-3 text-[13px] text-slate-700">
                  Approved tutor phone changes are locked. Contact support instead.
                </div>
              ) : null}
              
              {!isApprovedListedTutor && phoneStep === 0 && (
                <Button variant="secondary" onClick={() => { setOtp(""); setPhoneStep(1); }}>
                  Change Phone Number
                </Button>
              )}
              {!isApprovedListedTutor && phoneStep === 1 && (
                <div className="space-y-4">
                  <Input 
                    label="New Phone Number"
                    type="tel"
                    value={newPhone}
                    onChange={(e) => setNewPhone(sanitizeMobileNumberInput(e.target.value))}
                    placeholder="+2348012345678"
                    helperText="Use +234 followed by 10 digits."
                    error={newPhoneError ?? undefined}
                  />
                  <div className="flex gap-3">
                    <Button variant="secondary" onClick={requestPhoneOtp} disabled={!newPhone.trim() || Boolean(newPhoneError)}>
                      Send OTP
                    </Button>
                    <Button variant="ghost" onClick={() => setPhoneStep(0)}>
                      Cancel
                    </Button>
                  </div>
                </div>
              )}
              {!isApprovedListedTutor && phoneStep === 2 && (
                <div className="space-y-4">
                  <Input 
                    label="Enter OTP"
                    value={otp}
                    onChange={(e) => setOtp(e.target.value)}
                    placeholder="Enter the 6-character code"
                  />
                  <div className="flex gap-3">
                    <Button onClick={confirmPhoneChange}>
                      Update Phone Number
                    </Button>
                    <OtpResendButton onResend={requestPhoneOtp} />
                    <Button variant="ghost" onClick={() => setPhoneStep(0)}>
                      Cancel
                    </Button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Account Management */}
      <div className="space-y-6">
        <div className="text-[20px] font-semibold">Account Management</div>

        {/* Freeze Account */}
        <div className="form-panel rounded-2xl p-6">
          <div className="mb-6 flex items-start gap-4">
            <div className="rounded-full bg-orange-50 p-3">
              <Shield className="w-6 h-6 text-orange-600" />
            </div>
            <div className="flex-1">
              <h3 className="text-[18px] font-semibold mb-2">Freeze Account</h3>
              <p className="mb-4 text-[14px] text-black/65">Temporarily disable your account for a specified period</p>
              
              {me?.isFrozen && me.freezeUntil && new Date(me.freezeUntil) > new Date() ? (
                <div className="space-y-3">
                  <div className="text-[14px] text-black/65">
                    Your account is frozen until {new Date(me.freezeUntil).toLocaleString()}.
                  </div>
                  <Button variant="secondary" onClick={unfreezeAccount}>
                    Unfreeze Account
                  </Button>
                </div>
              ) : null}

              {(!me?.isFrozen || !me.freezeUntil || new Date(me.freezeUntil) <= new Date()) && freezeStep === 0 ? (
                <Button variant="secondary" onClick={() => setFreezeStep(1)}>
                  Freeze Account
                </Button>
              ) : null}

              {freezeStep === 1 ? (
                <div className="space-y-4">
                  <div className="grid gap-3 md:grid-cols-2">
                    <Input
                      label="Freeze start date"
                      type="date"
                      value={freezeStartsOn}
                      onChange={(e) => setFreezeStartsOn(e.target.value)}
                    />
                    <Input
                      label="Freeze end date"
                      type="date"
                      value={freezeEndsOn}
                      onChange={(e) => setFreezeEndsOn(e.target.value)}
                    />
                  </div>
                  <div className="text-[13px] text-black/55">
                    Select the dates you want your account frozen (maximum of 3 months).
                  </div>
                  <div className="flex gap-3">
                    <Button variant="secondary" onClick={requestFreezeOtp} disabled={!freezeStartsOn || !freezeEndsOn}>
                      Send OTP
                    </Button>
                    <Button variant="ghost" onClick={() => setFreezeStep(0)}>
                      Cancel
                    </Button>
                  </div>
                </div>
              ) : null}

              {freezeStep === 2 ? (
                <div className="space-y-4">
                  <Input
                    label="Enter OTP"
                    value={otp}
                    onChange={(e) => setOtp(e.target.value)}
                    placeholder="Enter the 6-character code"
                  />
                  <div className="flex gap-3">
                    <Button variant="destructive" onClick={confirmFreeze}>
                      Confirm Freeze
                    </Button>
                    <OtpResendButton onResend={requestFreezeOtp} />
                    <Button variant="ghost" onClick={() => setFreezeStep(0)}>
                      Cancel
                    </Button>
                  </div>
                </div>
              ) : null}
            </div>
          </div>
        </div>

        {/* Delete Account */}
        <div className="rounded-2xl border border-red-200 bg-red-50/50 p-6">
          <div className="flex items-start gap-4 mb-6">
            <div className="p-3 rounded-full bg-red-50">
              <UserX className="w-6 h-6 text-red-600" />
            </div>
            <div className="flex-1">
              <h3 className="text-[18px] font-semibold mb-2 text-red-900">Delete Account</h3>
              <p className="text-[14px] text-red-700 mb-4">Permanently delete your account and all associated data. This action cannot be undone.</p>
              
              {deleteStep === 0 ? (
                <Button variant="destructive" onClick={() => setDeleteStep(1)}>
                  Delete Account
                </Button>
              ) : null}

              {deleteStep === 1 ? (
                <div className="space-y-4">
                  <div className="p-4 bg-red-100 rounded-lg border border-red-200">
                    <p className="text-[14px] text-red-800 font-medium mb-2">Do you really want to delete this account?</p>
                    <p className="text-[13px] text-red-700">
                      This action is irreversible and you will lose all data. You could freeze your account and pay only N200/month subscription fee.
                    </p>
                  </div>
                  <div className="flex gap-3">
                    <Button variant="destructive" onClick={requestDeleteOtp}>
                      Yes
                    </Button>
                    <Button variant="secondary" onClick={() => setDeleteStep(0)}>
                      No
                    </Button>
                  </div>
                </div>
              ) : null}

              {deleteStep === 2 ? (
                <div className="space-y-4">
                  <div className="p-4 bg-red-100 rounded-lg border border-red-200">
                    <p className="text-[14px] text-red-800 font-medium mb-2">Warning: This action is irreversible</p>
                    <p className="text-[13px] text-red-700">Once you delete your account, all your data will be permanently removed. You will not be able to recover your account.</p>
                  </div>
                  <Input
                    label="Enter OTP"
                    value={otp}
                    onChange={(e) => setOtp(e.target.value)}
                    placeholder="Enter the 6-character code"
                  />
                  <div className="flex gap-3">
                    <Button variant="destructive" onClick={deleteAccount}>
                      Delete Account
                    </Button>
                    <OtpResendButton onResend={requestDeleteOtp} />
                    <Button variant="ghost" onClick={() => setDeleteStep(0)}>
                      Cancel
                    </Button>
                  </div>
                </div>
              ) : null}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
