import json
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from apps.backoffice.models import Booking


@csrf_exempt
def asaas_webhook(request):
    """
    Rota que escuta os eventos do Asaas com validação de token seguro.
    """
    if request.method == 'POST':
        # Validação do Token de autenticação do Webhook Asaas
        expected_token = getattr(settings, 'ASAAS_WEBHOOK_TOKEN', None)
        if expected_token:
            received_token = request.headers.get('asaas-access-token')
            if received_token != expected_token:
                return JsonResponse({'error': 'Não autorizado: token de webhook inválido'}, status=401)

        try:
            payload = json.loads(request.body)
            event = payload.get('event')
            payment_data = payload.get('payment', {})

            # O evento que nos interessa: Pagamento Recebido
            if event == 'PAYMENT_RECEIVED':
                # Buscamos o ID da reserva que enviamos na hora de criar o Pix
                booking_id = payment_data.get('externalReference')

                if booking_id:
                    booking = Booking.objects.filter(id=booking_id).first()

                    if booking and booking.status == 'PENDING':
                        last_payment = booking.payments.filter(status='PENDING').last() or booking.payments.last()
                        if last_payment:
                            last_payment.status = 'PAID'
                            fields_to_update = ['status']
                            receipt_url = payment_data.get('transactionReceiptUrl')
                            invoice_url = payment_data.get('invoiceUrl')
                            if receipt_url:
                                last_payment.bank_receipt_url = receipt_url
                                fields_to_update.append('bank_receipt_url')
                            if invoice_url:
                                last_payment.invoice_url = invoice_url
                                fields_to_update.append('invoice_url')
                            last_payment.save(update_fields=fields_to_update)

                        if last_payment and last_payment.strategy == 'PARTIAL':
                            booking.payment_status = 'PARTIAL'
                            booking.amount_paid = last_payment.amount
                        else:
                            booking.payment_status = 'PAID'
                            booking.amount_paid = booking.price

                        booking.status = 'CONFIRMED'
                        booking.save()
                        print(f"✅ SUCESSO: Reserva {booking.id} paga via Webhook!")

            return JsonResponse({'received': True}, status=200)

        except json.JSONDecodeError:
            return JsonResponse({'error': 'JSON Inválido'}, status=400)
        except Exception as e:
            print(f"❌ ERRO WEBHOOK: {e}")
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Método não permitido'}, status=405)