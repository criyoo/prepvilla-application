from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.files.storage import default_storage
from rest_framework.test import APIClient
from django.conf import settings
import re

from core.models import AppUser


class UploadTests(TestCase):
  def setUp(self):
    self.client = APIClient()
    self.student = AppUser.objects.create_user(
      email="student_upload@example.com",
      password="student123",
      role="student",
      display_name="Student",
      full_name="Ada Lovelace",
      timezone="UTC",
      is_verified=True,
    )
    self.tutor = AppUser.objects.create_user(
      email="tutor_upload@example.com",
      password="tutor123",
      role="tutor",
      display_name="Tutor",
      full_name="Alan Turing",
      timezone="UTC",
      is_verified=True,
    )
    self.saved_paths: list[str] = []

  def tearDown(self):
    for p in self.saved_paths:
      try:
        default_storage.delete(p)
      except Exception:
        pass

  def _store_path_from_url(self, url: str) -> str:
    media_url = settings.MEDIA_URL
    if url.startswith(media_url):
      return url[len(media_url):]
    return url.lstrip("/")

  def test_student_photo_upload_saved_under_students_folder(self):
    self.client.force_authenticate(user=self.student)
    f = SimpleUploadedFile("avatar.png", b"fakepng", content_type="image/png")
    res = self.client.post("/api/uploads", data={"file": f, "kind": "photo", "location": "Lagos"}, format="multipart")
    self.assertEqual(res.status_code, 200)
    data = res.json()
    self.assertIn("/uploads/images/students/", data["url"])
    self.assertRegex(data["name"], r"^photo_ada_lovelace_[0-9a-f]{32}\.png$")
    path = self._store_path_from_url(data["url"])
    self.saved_paths.append(path)
    self.assertTrue(default_storage.exists(path))

  def test_tutor_documents_upload_saved_under_tutors_folder(self):
    self.client.force_authenticate(user=self.tutor)
    f = SimpleUploadedFile("nin.pdf", b"fakepdf", content_type="application/pdf")
    res = self.client.post("/api/uploads", data={"file": f, "kind": "id_document", "location": "Ikeja_Lagos"}, format="multipart")
    self.assertEqual(res.status_code, 200)
    data = res.json()
    self.assertIn("/uploads/images/tutors/", data["url"])
    self.assertRegex(data["name"], r"^id_alan_turing_[0-9a-f]{32}\.pdf$")
    path = self._store_path_from_url(data["url"])
    self.saved_paths.append(path)
    self.assertTrue(default_storage.exists(path))

  def test_tutor_additional_document_upload_saved_under_documents_folder(self):
    self.client.force_authenticate(user=self.tutor)
    f = SimpleUploadedFile("extra.pdf", b"fakepdf", content_type="application/pdf")
    res = self.client.post("/api/uploads", data={"file": f, "kind": "additional_document"}, format="multipart")
    self.assertEqual(res.status_code, 200)
    data = res.json()
    self.assertIn("/uploads/documents/tutors/", data["url"])
    self.assertRegex(data["name"], r"^additional_alan_turing_[0-9a-f]{32}\.pdf$")
    path = self._store_path_from_url(data["url"])
    self.saved_paths.append(path)
    self.assertTrue(default_storage.exists(path))

  def test_upload_suffix_is_stable_per_user(self):
    self.client.force_authenticate(user=self.tutor)
    photo = SimpleUploadedFile("avatar.jpg", b"fakejpg", content_type="image/jpeg")
    id_doc = SimpleUploadedFile("id.png", b"fakepng", content_type="image/png")
    res_photo = self.client.post("/api/uploads", data={"file": photo, "kind": "photo"}, format="multipart")
    self.assertEqual(res_photo.status_code, 200)
    res_id = self.client.post("/api/uploads", data={"file": id_doc, "kind": "id_document"}, format="multipart")
    self.assertEqual(res_id.status_code, 200)

    name_photo = res_photo.json()["name"]
    name_id = res_id.json()["name"]
    suffix_photo = name_photo.rsplit("_", 1)[-1].split(".", 1)[0]
    suffix_id = name_id.rsplit("_", 1)[-1].split(".", 1)[0]
    self.assertEqual(suffix_photo, suffix_id)
