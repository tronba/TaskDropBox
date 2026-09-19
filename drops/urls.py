from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("teacher/", views.teacher_home, name="teacher_home"),
    path("create/login/", views.creator_login, name="creator_login"),
    path("create/", views.task_create, name="task_create"),
    path("open/", views.open_student, name="open_student"),
    path("manage/open/", views.open_admin, name="open_admin"),
    path("d/<str:student_token>/", views.student_task, name="student_task"),
    path("d/<str:student_token>/submit/", views.submit_task, name="submit_task"),
    path(
        "d/<str:student_token>/task-file/<uuid:file_id>/",
        views.task_attachment_download,
        name="task_attachment_download",
    ),
    path("receipt/<str:receipt_id>/", views.submission_receipt, name="submission_receipt"),
    path("a/<str:admin_token>/", views.admin_exchange, name="admin_exchange"),
    path("manage/<uuid:task_id>/", views.manage_task, name="manage_task"),
    path("manage/<uuid:task_id>/close/", views.close_task, name="close_task"),
    path("manage/<uuid:task_id>/reopen/", views.reopen_task, name="reopen_task"),
    path("manage/<uuid:task_id>/export.zip", views.export_task, name="export_task"),
    path(
        "manage/<uuid:task_id>/file/<uuid:file_id>/",
        views.submission_file_download,
        name="submission_file_download",
    ),
    path(
        "manage/<uuid:task_id>/task-file/<uuid:file_id>/",
        views.admin_task_attachment_download,
        name="admin_task_attachment_download",
    ),
    path(
        "manage/<uuid:task_id>/submission/<uuid:submission_id>/delete/",
        views.delete_submission_view,
        name="delete_submission",
    ),
    path("manage/<uuid:task_id>/delete/", views.delete_task_view, name="delete_task"),
    path("healthz", views.health, name="health"),
    path("source/", views.source_archive, name="source_archive"),
]
