# apps/scheduler/views/payments/payment_views.py
from datetime import timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse
from apps.backoffice.models import Booking, Payment
from apps.backoffice.services import gerar_pagamento_pix_asaas


from django.conf import settings


def checkout_view(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)

    # Se está confirmada, manda direto para o Ticket de Sucesso!
    if booking.status == 'CONFIRMED':
        return redirect('scheduler:booking_success', arena_slug=booking.arena.slug, booking_id=booking.id)

    # Bloqueio de segurança em modo de demonstração
    if getattr(settings, 'DEMO_MODE', True):
        messages.warning(
            request,
            "🔒 Modo Demonstração: Os pagamentos online via PIX real estão desativados nesta versão de testes para evitar cobranças reais. O teste completo do sistema está disponível no Painel do Gestor."
        )
        return redirect('scheduler:arena_home', arena_slug=booking.arena.slug)

    # 1. VALIDAÇÃO DE SEGURANÇA ANTES DE CHAMAR O ASAAS
    if not booking.customer.cpf:
        messages.error(request, "CPF do cliente não encontrado. Por favor, tente refazer o agendamento.")
        booking.delete()
        return redirect('scheduler:arena_home', arena_slug=booking.arena.slug)

    # 2. Verifica se já existe um Pix pendente
    last_payment = booking.payments.filter(
        status='PENDING',
        pix_qr_code__isnull=False
    ).exclude(pix_qr_code='').last()

    pix_data = None

    if last_payment:
        pix_data = {
            'qr_code': last_payment.pix_qr_code,
            'qr_code_base64': last_payment.pix_qr_code_base64,
            'amount': last_payment.amount
        }
    else:
        try:
            # Identifica se é pagamento parcial (sinal de 50%) ou integral (100%)
            is_partial = (request.GET.get('type') == 'partial') or (booking.payment_status == 'PARTIAL') or (last_payment and last_payment.strategy == 'PARTIAL')
            amount_to_pay = (booking.price / 2) if is_partial else booking.price

            # GERA NOVO NO ASAAS PASSANDO A VARIÁVEL CORRETA
            pix_response = gerar_pagamento_pix_asaas(booking, amount_to_pay)

            payment = Payment.objects.create(
                booking=booking,
                transaction_id=pix_response['transaction_id'],
                amount=pix_response['amount'],
                status='PENDING',
                pix_qr_code=pix_response['qr_code'],
                pix_qr_code_base64=pix_response['qr_code_base64'],
                invoice_url=pix_response.get('invoice_url'),
                bank_receipt_url=pix_response.get('bank_receipt_url'),
                strategy='PARTIAL' if is_partial else 'TOTAL'
            )

            pix_data = {
                'qr_code': payment.pix_qr_code,
                'qr_code_base64': payment.pix_qr_code_base64,
                'amount': payment.amount
            }

        except Exception as e:
            print(f"ERRO ASAAS NO CHECKOUT: {e}")
            messages.error(request, f"Erro ao gerar pagamento PIX: {e}")
            return redirect('scheduler:arena_home', arena_slug=booking.arena.slug)

    elapsed_seconds = (timezone.now() - booking.created_at).total_seconds() if booking.created_at else 0
    remaining_seconds = max(0, int(900 - elapsed_seconds))

    return render(request, 'scheduler/booking/payment_pending.html', {
        'booking': booking,
        'pix_data': pix_data,
        'remaining_seconds': remaining_seconds
    })


def check_payment_status(request, booking_id):
    """ Devolve o status atual da reserva para o JavaScript """
    booking = get_object_or_404(Booking, id=booking_id)
    return JsonResponse({'status': booking.status})