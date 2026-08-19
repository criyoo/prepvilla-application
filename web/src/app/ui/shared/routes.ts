export function buildTutorProfileHref(tutorId: string) {
  const params = new URLSearchParams({ id: tutorId });
  return `/tutors/?${params.toString()}`;
}
