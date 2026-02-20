from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Reservation

@login_required
def reservation_detail_api(request, pk):
    reservation = get_object_or_404(Reservation, pk=pk)

    # Optional: ensure user owns the reservation
    if request.user.is_anonymous or (request.user.userProfile.user_role not in ['A', 'S', 'D'] and reservation.user != request.user.userProfile):
        return JsonResponse({"error": "Unauthorized"}, status=403)

    data = {
        "id": reservation.id,
        "user": reservation.user.user.get_full_name(),
        "user_role": request.user.userProfile.user_role,
        "email": reservation.user.user.email,
        "workplace": reservation.reservation_to_work_place.work_place.name,
        "activity": reservation.get_activity_name(),
    }
    address = None
    if hasattr(reservation, "delivery_address"):
        address = reservation.delivery_address.street_address_1
        if reservation.delivery_address.street_address_2:
            address += "<br> %s" % reservation.delivery_address.street_address_2
        if reservation.delivery_address.city:
            address += "<br> %s" % reservation.delivery_address.city
        if reservation.delivery_address.state:
            address += ", %s" % reservation.delivery_address.state
        if reservation.delivery_address.zip_code:
            address += " %s" % reservation.delivery_address.zip_code
    elif reservation.reservation_to_work_place:
        workplace = reservation.reservation_to_work_place.work_place
        address = workplace.street_address_1
        if workplace.street_address_2:
            address += "<br> %s" % workplace.street_address_2
        if workplace.city:
            address += "<br> %s" % workplace.city
        if workplace.state:
            address += ", %s" % workplace.state
        if workplace.zip_code:
            address += " %s" % workplace.zip_code
    data["address"] = address

    return JsonResponse(data)
