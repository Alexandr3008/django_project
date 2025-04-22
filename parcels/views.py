import logging
from django.core.cache import cache
from django.shortcuts import render, redirect
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from .models import Parcel, ParcelType
from .serializers import ParcelSerializer, ParcelTypeSerializer

logger = logging.getLogger(__name__)

class RegisterParcelView(APIView):
    """Регистрация новой посылки для текущей сессии."""
    def post(self, request):
        session_key = request.session.session_key
        if not session_key:
            request.session.create()
            session_key = request.session.session_key

        data = request.data.copy()
        data['session_key'] = session_key
        serializer = ParcelSerializer(data=data)
        if serializer.is_valid():
            parcel = serializer.save(session_key=session_key)
            logger.info(f"Посылка {parcel.id} зарегистрирована для сессии {session_key}")
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        logger.error(f"Ошибка регистрации посылки: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ParcelTypeListView(APIView):
    """Список всех типов посылок."""
    def get(self, request):
        types = ParcelType.objects.all()
        serializer = ParcelTypeSerializer(types, many=True)
        return Response(serializer.data)

class ParcelListView(APIView):
    """Список посылок текущей сессии с фильтрацией и пагинацией."""
    def get(self, request):
        session_key = request.session.session_key
        if not session_key:
            return Response({"detail": "Нет активной сессии"}, status=status.HTTP_400_BAD_REQUEST)

        queryset = Parcel.objects.filter(session_key=session_key)
        type_filter = request.query_params.get('type', None)
        cost_calculated = request.query_params.get('cost_calculated', None)

        if type_filter:
            queryset = queryset.filter(type__id=type_filter)
        if cost_calculated == 'true':
            queryset = queryset.exclude(delivery_cost__isnull=True)
        elif cost_calculated == 'false':
            queryset = queryset.filter(delivery_cost__isnull=True)

        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = ParcelSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

class ParcelDetailView(APIView):
    """Детали конкретной посылки."""
    def get(self, request, parcel_id):
        session_key = request.session.session_key
        if not session_key:
            return Response({"detail": "Нет активной сессии"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            parcel = Parcel.objects.get(id=parcel_id, session_key=session_key)
            serializer = ParcelSerializer(parcel)
            return Response(serializer.data)
        except Parcel.DoesNotExist:
            logger.warning(f"Посылка {parcel_id} не найдена для сессии {session_key}")
            return Response({"detail": "Посылка не найдена"}, status=status.HTTP_404_NOT_FOUND)

def register_parcel_web(request):
    """Веб-страница для регистрации посылки."""
    if request.method == 'POST':
        session_key = request.session.session_key
        if not session_key:
            request.session.create()
            session_key = request.session.session_key

        data = {
            'name': request.POST.get('name'),
            'weight': request.POST.get('weight'),
            'type': request.POST.get('type'),
            'value': request.POST.get('value'),
            'session_key': session_key
        }
        serializer = ParcelSerializer(data=data)
        if serializer.is_valid():
            parcel = serializer.save()
            logger.info(f"Посылка {parcel.id} зарегистрирована через веб для сессии {session_key}")
            return redirect('parcel_list_web')
        else:
            logger.error(f"Ошибка регистрации через веб: {serializer.errors}")
            return render(request, 'register_parcel.html', {'errors': serializer.errors, 'types': ParcelType.objects.all()})

    return render(request, 'register_parcel.html', {'types': ParcelType.objects.all()})

def parcel_list_web(request):
    """Веб-страница со списком посылок."""
    session_key = request.session.session_key
    if not session_key:
        request.session.create()
        session_key = request.session.session_key

    parcels = Parcel.objects.filter(session_key=session_key)
    type_filter = request.GET.get('type', None)
    cost_calculated = request.GET.get('cost_calculated', None)

    if type_filter:
        parcels = parcels.filter(type__id=type_filter)
    if cost_calculated == 'true':
        parcels = parcels.exclude(delivery_cost__isnull=True)
    elif cost_calculated == 'false':
        parcels = parcels.filter(delivery_cost__isnull=True)

    return render(request, 'parcel_list.html', {
        'parcels': parcels,
        'types': ParcelType.objects.all(),
        'type_filter': type_filter,
        'cost_calculated': cost_calculated
    })

def parcel_types_web(request):
    """Веб-страница со списком типов посылок."""
    types = ParcelType.objects.all()
    return render(request, 'parcel_types.html', {'types': types})

def parcel_detail_web(request, parcel_id):
    """Веб-страница с деталями посылки."""
    session_key = request.session.session_key
    if not session_key:
        request.session.create()
        session_key = request.session.session_key

    try:
        parcel = Parcel.objects.get(id=parcel_id, session_key=session_key)
        return render(request, 'parcel_detail.html', {'parcel': parcel})
    except Parcel.DoesNotExist:
        logger.warning(f"Посылка {parcel_id} не найдена для сессии {session_key}")
        return render(request, 'parcel_detail.html', {'error': 'Посылка не найдена'})