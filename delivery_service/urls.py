from django.urls import path

from parcels import views

urlpatterns = [
    # API маршруты
    path("parcels/register/", views.RegisterParcelView.as_view(), name="register_parcel"),
    path("parcels/types/", views.ParcelTypeListView.as_view(), name="parcel_types"),
    path("parcels/", views.ParcelListView.as_view(), name="parcel_list"),
    path("parcels/<int:parcel_id>/", views.ParcelDetailView.as_view(), name="parcel_detail"),

    # Веб-маршруты
    path("", views.parcel_list_web, name="parcel_list_web"),  # Главная страница
    path("register/", views.register_parcel_web, name="register_parcel_web"),
    path("types/", views.parcel_types_web, name="parcel_types_web"),
    path("parcel/<int:parcel_id>/", views.parcel_detail_web, name="parcel_detail_web"),

]

