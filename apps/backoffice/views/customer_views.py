from django.urls import reverse_lazy, reverse
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from apps.backoffice.mixins import ArenaOwnerRequiredMixin
from apps.backoffice.models import Customer, Arena
from apps.backoffice.forms.customer_forms import CustomerForm
from django.db.models import Q

from django.shortcuts import redirect
from django.contrib import messages
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.template.loader import render_to_string


class CustomerListView(ArenaOwnerRequiredMixin, ListView):
    model = Customer
    template_name = 'backoffice/customers/customer_list.html'
    context_object_name = 'customers'

    paginate_by = 20

    def get_queryset(self):
        arena = Arena.objects.get(slug=self.kwargs['arena_slug'])
        
        queryset = Customer.objects.filter(arena=arena).order_by('name', 'id')
        
        q = self.request.GET.get('q')
        if q:
            queryset = queryset.filter(
                Q(name__icontains=q) | 
                Q(phone__icontains=q) |
                Q(email__icontains=q)
            )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        arena = Arena.objects.get(slug=self.kwargs['arena_slug'])
        context['arena'] = arena
        
        # Next page URL
        page_obj = context.get('page_obj')
        if page_obj and page_obj.has_next():
            qp_next = self.request.GET.copy()
            qp_next['page'] = page_obj.next_page_number()
            context['next_page_url'] = f"?{qp_next.urlencode()}"
        else:
            context['next_page_url'] = None
            
        return context

    def render_to_response(self, context, **response_kwargs):
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            page_obj = context.get('page_obj')
            html = render_to_string(
                'backoffice/customers/_customer_rows.html',
                context,
                request=self.request
            )
            has_next = page_obj.has_next() if page_obj else False
            next_url = None
            if has_next:
                qp = self.request.GET.copy()
                qp['page'] = page_obj.next_page_number()
                next_url = f"?{qp.urlencode()}"
                
            return JsonResponse({
                'html': html,
                'has_next': has_next,
                'next_url': next_url,
            })
        return super().render_to_response(context, **response_kwargs)


class CustomerCreateView(ArenaOwnerRequiredMixin, CreateView):
    model = Customer
    form_class = CustomerForm
    template_name = 'backoffice/customers/customer_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['arena'] = Arena.objects.get(slug=self.kwargs['arena_slug'])
        context['titulo_pagina'] = 'Novo Cliente'
        return context

    def form_valid(self, form):
        arena = Arena.objects.get(slug=self.kwargs['arena_slug'])
        form.instance.arena = arena
        self.object = form.save()
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': 'Cliente cadastrado com sucesso!',
                'customer': {
                    'id': self.object.id,
                    'name': self.object.name,
                    'phone': self.object.phone,
                    'formatted_phone': self.object.formatted_phone,
                }
            })
        messages.success(self.request, "Cliente cadastrado com sucesso!")
        return redirect(self.get_success_url())

    def form_invalid(self, form):
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            errors = {}
            for field, error_list in form.errors.items():
                errors[field] = [str(e) for e in error_list]
            return JsonResponse({
                'success': False,
                'errors': errors
            }, status=400)
        return super().form_invalid(form)

    def get_success_url(self):
        arena_slug = self.kwargs['arena_slug']
        next_url = self.request.GET.get('next')
        if next_url:
            return next_url
        return reverse('backoffice:customer_list', kwargs={'arena_slug': arena_slug})


class CustomerDetailView(ArenaOwnerRequiredMixin, DetailView):
    model = Customer
    template_name = 'backoffice/customers/customer_detail.html'
    context_object_name = 'customer'

    def get_queryset(self):
        return Customer.objects.filter(arena__slug=self.kwargs['arena_slug'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['arena'] = Arena.objects.get(slug=self.kwargs['arena_slug'])
        return context


class CustomerUpdateView(ArenaOwnerRequiredMixin, UpdateView):
    model = Customer
    form_class = CustomerForm
    template_name = 'backoffice/customers/customer_form.html'

    def get_queryset(self):
        return Customer.objects.filter(arena__slug=self.kwargs['arena_slug'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['arena'] = Arena.objects.get(slug=self.kwargs['arena_slug'])
        context['titulo_pagina'] = 'Editar Cliente'
        return context

    def form_valid(self, form):
        self.object = form.save()
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': 'Cliente atualizado com sucesso!',
                'customer': {
                    'id': self.object.id,
                    'name': self.object.name,
                    'phone': self.object.phone,
                    'formatted_phone': self.object.formatted_phone,
                }
            })
        messages.success(self.request, "Cliente atualizado com sucesso!")
        return redirect(self.get_success_url())

    def form_invalid(self, form):
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            errors = {}
            for field, error_list in form.errors.items():
                errors[field] = [str(e) for e in error_list]
            return JsonResponse({
                'success': False,
                'errors': errors
            }, status=400)
        return super().form_invalid(form)

    def get_success_url(self):
        return reverse('backoffice:customer_list', kwargs={'arena_slug': self.kwargs['arena_slug']})


class CustomerDeleteView(ArenaOwnerRequiredMixin, DeleteView):
    model = Customer
    template_name = 'backoffice/customers/customer_confirm_delete.html'

    def get_queryset(self):
        return Customer.objects.filter(arena__slug=self.kwargs['arena_slug'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['arena'] = Arena.objects.get(slug=self.kwargs['arena_slug'])
        return context

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        customer_name = self.object.name
        self.object.delete()
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': f"Cliente '{customer_name}' excluído com sucesso!"
            })
        messages.success(request, f"Cliente '{customer_name}' excluído com sucesso!")
        return redirect(self.get_success_url())

    def post(self, request, *args, **kwargs):
        return self.delete(request, *args, **kwargs)

    def get_success_url(self):
        return reverse_lazy('backoffice:customer_list', kwargs={'arena_slug': self.kwargs['arena_slug']})


@login_required
def get_customer_data(request, customer_id):
    """Retorna dados do cliente em JSON para preencher formulários via AJAX com validação de posse da arena."""
    try:
        customer = Customer.objects.select_related('arena').get(pk=customer_id)
        if not (request.user.is_superuser or request.user in customer.arena.users.all()):
            return JsonResponse({'error': 'Acesso não autorizado'}, status=403)
        data = {
            'id': customer.id,
            'name': customer.name,
            'phone': customer.phone,
            'formatted_phone': customer.formatted_phone,
            'email': customer.email or '',
            'cpf': customer.cpf or '',
            'birth_date': customer.birth_date.strftime('%Y-%m-%d') if customer.birth_date else '',
            'observation': customer.observation or '',
        }
        return JsonResponse(data)
    except Customer.DoesNotExist:
        return JsonResponse({'error': 'Cliente não encontrado'}, status=404)


@login_required
def search_customers_ajax(request, arena_slug):
    """
    Pesquisa clientes da arena por nome, telefone ou CPF.
    Retorna resultados em formato JSON para autocomplete dinâmico com validação de permissão.
    """
    from django.shortcuts import get_object_or_404
    arena = get_object_or_404(Arena, slug=arena_slug)
    if not (request.user.is_superuser or request.user in arena.users.all()):
        return JsonResponse({'error': 'Acesso não autorizado', 'customers': []}, status=403)

    query = request.GET.get('q', '').strip()

    if not query or len(query) < 2:
        return JsonResponse({'customers': []})

    clean_digits = ''.join(filter(str.isdigit, query))

    q_filter = Q(name__icontains=query)
    if clean_digits:
        q_filter |= Q(phone__icontains=clean_digits)
        if len(clean_digits) >= 3:
            q_filter |= Q(cpf__icontains=clean_digits)

    customers = Customer.objects.filter(arena=arena).filter(q_filter).order_by('name')[:15]

    data = []
    for c in customers:
        data.append({
            'id': c.id,
            'name': c.name,
            'phone': c.phone,
            'formatted_phone': c.formatted_phone,
            'cpf': c.cpf or '',
            'email': c.email or '',
        })

    return JsonResponse({'customers': data})