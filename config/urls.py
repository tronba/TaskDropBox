from django.urls import include, path

urlpatterns = [
    path("i18n/", include("django.conf.urls.i18n")),
    path("", include("drops.urls")),
]

handler404 = "drops.views.not_found"
handler500 = "drops.views.server_error"
