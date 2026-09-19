from django.urls import include, path

urlpatterns = [path("", include("drops.urls"))]

handler404 = "drops.views.not_found"
handler500 = "drops.views.server_error"
