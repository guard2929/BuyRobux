import re
import requests
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.conf import settings
from django.utils import timezone
from decimal import Decimal, InvalidOperation
from .models import CustomUser, Purchase, Withdrawal
from .forms import LoginForm
from nowpay import NOWPayments
from django.conf import settings
from django.shortcuts import redirect, render
from .models import Purchase
from decimal import Decimal
import hmac
import hashlib
import json
from django.http import HttpResponse
from .models import Purchase
from django.conf import settings
from django.shortcuts import render, get_object_or_404
from .models import Purchase, CustomUser
from decimal import Decimal
from .models import CurrencyRate, PromoCode, PromoCodeActivation


def index(request):
    context = {}
    recent_purchases = Purchase.objects.select_related('user').order_by('-created_at')[:3]
    context['recent_purchases'] = recent_purchases
    language = request.GET.get('lang', 'ru')
    context['language'] = language
    if request.user.is_authenticated:
        purchases = Purchase.objects.filter(user=request.user).order_by('-created_at')
        context['purchases'] = purchases
        context['user_promo_code'] = request.user.promo_code
        context['bonus_balance'] = request.user.bonus_balance
        context['invited_friends_count'] = 0
        context['bonus_earned'] = 0
    return render(request, 'core/index.html', context)


@login_required
@require_POST
def activate_promo(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Нужно войти'}, status=403)

    promo_code_value = request.POST.get('promo_code', '').strip().upper()

    try:
        promo = PromoCode.objects.get(code=promo_code_value, is_active=True)

        # Проверка срока действия
        if promo.valid_until and promo.valid_until < timezone.now():
            return JsonResponse({'error': 'Срок действия промокода истек'}, status=400)

        # Проверка предыдущей активации
        if not request.user.can_activate_promo(promo):
            return JsonResponse({'error': 'Вы уже активировали этот промокод'}, status=400)

        if promo.promo_type == 'friend':
            return JsonResponse({'error': 'Дружеские промокоды используются при покупке, а не активируются здесь.'},
                                status=400)
        else:
            # Для общих промокодов - мгновенное начисление
            request.user.bonus_balance += promo.bonus_amount
            request.user.save()

            # Фиксируем активацию
            PromoCodeActivation.objects.create(
                user=request.user,
                promo_code=promo
            )

            return JsonResponse({
                'success': f'Вам начислено {promo.bonus_amount} бонусных R$!'
            })

    except PromoCode.DoesNotExist:
        return JsonResponse({'error': 'Неверный промокод'}, status=400)


class CurrencyRatesMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Добавляем курсы валют в объект запроса
        request.rub_rate = self.get_rate('RUB', default=Decimal('0.76'))
        request.usd_rate = self.get_rate('USD', default=Decimal('0.016'))

        response = self.get_response(request)
        return response

    def get_rate(self, currency, default):
        try:
            return CurrencyRate.objects.get(currency=currency).rate
        except CurrencyRate.DoesNotExist:
            return default


def currency_rates(request):
    rates = {}
    for currency in ['RUB', 'USD']:
        try:
            rate_obj = CurrencyRate.objects.get(currency=currency)
            rates[f'{currency.lower()}_rate'] = rate_obj.rate
        except CurrencyRate.DoesNotExist:
            # Значения по умолчанию
            rates[f'{currency.lower()}_rate'] = Decimal('0.76') if currency == 'RUB' else Decimal('0.016')
    return rates


@login_required
def social_link(request, social):
    user = request.user
    if social == 'vk' and not user.vk_subscribed:
        user.vk_subscribed = True
        user.bonus_balance += 5
        user.save()
        return redirect('https://vk.com/your_group')  # Замените на вашу группу VK
    elif social == 'discord' and not user.discord_joined:
        user.discord_joined = True
        user.bonus_balance += 5
        user.save()
        return redirect('https://discord.gg/your_server')  # Замените на ваш сервер Discord
    elif social == 'telegram' and not user.telegram_joined:
        user.telegram_joined = True
        user.bonus_balance += 5
        user.save()
        return redirect('https://t.me/your_channel')  # Замените на ваш канал Telegram
    else:
        if social == 'vk':
            return redirect('https://vk.com/your_group')
        elif social == 'discord':
            return redirect('https://discord.gg/your_server')
        elif social == 'telegram':
            return redirect('https://t.me/your_channel')
        else:
            return redirect('/')


@login_required
@require_POST
def buy_robux_step2(request):
    robux_steps = int(request.POST.get('robux_steps', 0))
    robux_amount = 20 + (robux_steps * 20)
    rub_rate = request.rub_rate
    price = robux_amount * rub_rate
    promo_code = request.POST.get('promo_code', '')

    if robux_amount < 20 or robux_amount > 5000:
        return render(request, 'core/index.html', {'error': 'Неверное количество Robux.'})

    discount = 0
    if promo_code:
        try:
            friend = CustomUser.objects.get(promo_code=promo_code)
            if friend == request.user:
                return render(request, 'core/index.html', {'error': 'Нельзя использовать свой промокод.'})
            discount = 0.05
            price = price * (1 - discount)
        except CustomUser.DoesNotExist:
            return render(request, 'core/index.html', {'error': 'Неверный промокод.'})

    places = get_roblox_places(request.user.roblox_nick)
    if not places:
        return render(request, 'core/step2.html', {
            'error': 'У вас нет доступных мест в Roblox.',
            'robux': robux_amount,
            'price': round(price, 2),
            'promo_code': promo_code,
        })
    context = {
        'robux': robux_amount,
        'price': round(price, 2),
        'places': places,
        'promo_code': promo_code,
    }
    return render(request, 'core/step2.html', context)


@login_required
@require_POST
def buy_robux_step3(request):
    robux_amount = int(request.POST.get('robux_amount', 0))
    price = float(request.POST.get('price', 0))
    place_id = request.POST.get('place_id', None)
    place_name = request.POST.get('place_name', '')
    promo_code = request.POST.get('promo_code', '')
    place_link = request.POST.get('place_link', '')
    action = request.POST.get('action')
    selected_gamepass_id = request.POST.get('selected_gamepass_id', None)

    if place_link and not place_id:
        match = re.search(r'games/(\d+)', place_link)
        if match:
            place_id = match.group(1)

    if not place_id:
        return render(request, 'core/step2.html', {
            'error': 'Выберите место или укажите корректную ссылку.',
            'robux_amount': robux_amount,
            'price': price,
            'places': get_roblox_places(request.user.roblox_nick),
            'promo_code': promo_code,
        })

    try:
        price_decimal = Decimal(str(price))
    except:
        price_decimal = Decimal('0.01')
    if price_decimal <= 0:
        price_decimal = Decimal('0.01')

    purchase = Purchase.objects.create(
        user=request.user,
        robux_amount=robux_amount,
        price=price_decimal,
        place_id=place_id,
        place_name=place_name,
        status='pending',
        promo_code_used=promo_code,
    )

    gamepass_price = round(price_decimal / Decimal('0.7'))

    universe_id = get_universe_id(place_id)
    if not universe_id:
        return render(request, 'core/../../SellRobux/step3.html', {
            'error': 'Не удалось получить universe_id для place_id.',
            'robux_amount': robux_amount,
            'price': price,
            'place_id': place_id,
            'place_name': place_name,
            'purchase_id': purchase.id,
            'promo_code': promo_code,
            'gamepass_price': gamepass_price,
            'place_link': place_link,
        })

    gamepasses = get_gamepasses(universe_id)
    if not gamepasses:
        return render(request, 'core/../../SellRobux/step3.html', {
            'error': 'Нет доступных Game Passes. Пожалуйста, создайте новый Game Pass.',
            'robux_amount': robux_amount,
            'price': price,
            'place_id': place_id,
            'place_name': place_name,
            'purchase_id': purchase.id,
            'promo_code': promo_code,
            'gamepass_price': gamepass_price,
            'place_link': place_link,
        })

    if action == 'check':
        if not selected_gamepass_id:
            return render(request, 'core/../../SellRobux/step3.html', {
                'error': 'Выберите существующий Game Pass или создайте новый.',
                'instruction': (
                    '1. Перейдите в Roblox Studio.\n'
                    '2. Откройте ваш плейс.\n'
                    '3. Создайте Game Pass или выберите существующий.\n'
                    f'4. Установите цену Game Pass на {gamepass_price} Robux.\n'
                    '5. Опубликуйте Game Pass и включите "For Sale".\n'
                    '6. Скопируйте ID Game Pass и выберите его здесь.'
                ),
                'robux_amount': robux_amount,
                'price': price,
                'place_id': place_id,
                'place_name': place_name,
                'purchase_id': purchase.id,
                'promo_code': promo_code,
                'gamepass_price': gamepass_price,
                'place_link': place_link,
                'universe_id': universe_id,
                'gamepasses': gamepasses,
            })

        matching_gamepass = next(
            (gp for gp in gamepasses if gp['id'] == selected_gamepass_id and gp['price'] == gamepass_price), None)
        if not matching_gamepass:
            return render(request, 'core/step3.html', {
                'error': f'Game Pass с ID {selected_gamepass_id} не найден или его цена не совпадает с {gamepass_price} R$.',
                'instruction': (
                    '1. Перейдите в Roblox Studio.\n'
                    '2. Откройте ваш плейс.\n'
                    '3. Создайте Game Pass или выберите существующий.\n'
                    f'4. Установите цену Game Pass на {gamepass_price} Robux.\n'
                    '5. Опубликуйте Game Pass и включите "For Sale".\n'
                    '6. Скопируйте ID Game Pass и выберите его здесь.'
                ),
                'robux_amount': robux_amount,
                'price': price,
                'place_id': place_id,
                'place_name': place_name,
                'purchase_id': purchase.id,
                'promo_code': promo_code,
                'gamepass_price': gamepass_price,
                'place_link': place_link,
                'universe_id': universe_id,
                'gamepasses': gamepasses,
            })

        purchase.gamepass_id = selected_gamepass_id
        purchase.gamepass_price = gamepass_price
        purchase.save()

    return render(request, 'core/step3.html', {
        'robux_amount': robux_amount,
        'price': price,
        'place_id': place_id,
        'place_name': place_name,
        'purchase_id': purchase.id,
        'promo_code': promo_code,
        'gamepass_price': gamepass_price,
        'place_link': place_link,
        'universe_id': universe_id,
        'gamepasses': gamepasses,
        'instruction': (
            '1. Перейдите в Roblox Studio.\n'
            '2. Откройте ваш плейс.\n'
            '3. Создайте Game Pass или выберите существующий.\n'
            f'4. Установите цену Game Pass на {gamepass_price} Robux.\n'
            '5. Опубликуйте Game Pass и включите "For Sale".\n'
            '6. Скопируйте ID Game Pass и выберите его здесь.'
        ),
    })


@login_required
@require_POST
def buy_confirm(request):
    purchase_id = request.POST.get('purchase_id')
    promo_code = request.POST.get('promo_code', '')
    selected_gamepass_id = request.POST.get('gamepass_id')
    try:
        purchase = Purchase.objects.get(id=purchase_id, user=request.user)
        place_id = purchase.place_id
        universe_id = get_universe_id(place_id)
        if not universe_id:
            return render(request, 'core/step3.html', {
                'error': f'Не удалось получить universe_id для place_id {place_id}.',
                'robux': purchase.robux_amount,
                'price': float(purchase.price),
                'place_id': place_id,
                'place_name': purchase.place_name,
                'purchase_id': purchase.id,
                'promo_code': purchase.promo_code_used,
                'gamepasses': get_gamepasses(universe_id),
                'gamepass_price': round(purchase.price / Decimal('0.7')),
                'instruction': (
                    "1. Выберите существующий GamePass или создайте новый с ценой {} Robux.\n"
                    "2. Опубликуйте и активируйте 'For Sale'.\n"
                    "3. Нажмите 'Проверить', затем 'Оплатить'.".format(round(purchase.price / Decimal('0.7')))
                ),
            })

        gamepasses = get_gamepasses(universe_id)
        if not gamepasses:
            return render(request, 'core/step3.html', {
                'error': f'Не удалось получить список GamePass для universe_id {universe_id}.',
                'robux': purchase.robux_amount,
                'price': float(purchase.price),
                'place_id': place_id,
                'place_name': purchase.place_name,
                'purchase_id': purchase.id,
                'promo_code': purchase.promo_code_used,
                'gamepasses': gamepasses,
                'gamepass_price': round(purchase.price / Decimal('0.7')),
                'instruction': (
                    "1. Выберите существующий GamePass или создайте новый с ценой {} Robux.\n"
                    "2. Опубликуйте и активируйте 'For Sale'.\n"
                    "3. Нажмите 'Проверить', затем 'Оплатить'.".format(round(purchase.price / Decimal('0.7')))
                ),
            })

        if not selected_gamepass_id:
            return render(request, 'core/step3.html', {
                'error': 'Выберите GamePass.',
                'robux': purchase.robux_amount,
                'price': float(purchase.price),
                'place_id': place_id,
                'place_name': purchase.place_name,
                'purchase_id': purchase.id,
                'promo_code': purchase.promo_code_used,
                'gamepasses': gamepasses,
                'gamepass_price': round(purchase.price / Decimal('0.7')),
                'instruction': (
                    "1. Выберите существующий GamePass или создайте новый с ценой {} Robux.\n"
                    "2. Опубликуйте и активируйте 'For Sale'.\n"
                    "3. Нажмите 'Проверить', затем 'Оплатить'.".format(round(purchase.price / Decimal('0.7')))
                ),
            })

        matching_gamepass = next((gp for gp in gamepasses if str(gp['id']) == selected_gamepass_id), None)
        expected_gamepass_price = round(purchase.price / Decimal('0.7'))
        if not matching_gamepass or matching_gamepass['price'] != expected_gamepass_price:
            return render(request, 'core/step3.html', {
                'error': f'GamePass должен стоить {expected_gamepass_price} Robux.',
                'robux': purchase.robux_amount,
                'price': float(purchase.price),
                'place_id': place_id,
                'place_name': purchase.place_name,
                'purchase_id': purchase.id,
                'promo_code': purchase.promo_code_used,
                'gamepasses': gamepasses,
                'gamepass_price': expected_gamepass_price,
                'instruction': (
                    "1. Выберите существующий GamePass или создайте новый с ценой {} Robux.\n"
                    "2. Опубликуйте и активируйте 'For Sale'.\n"
                    "3. Нажмите 'Проверить', затем 'Оплатить'.".format(expected_gamepass_price)
                ),
            })

        purchase.gamepass_id = selected_gamepass_id
        purchase.gamepass_price = matching_gamepass['price']
        purchase.status = 'completed'
        purchase.save()

        if promo_code:
            try:
                promo = PromoCode.objects.get(code=promo_code, promo_type='friend')
                friend = promo.created_by

                if friend != request.user:
                    # Проверяем, первая ли это завершенная покупка покупателя
                    if Purchase.objects.filter(user=request.user, status='completed').count() == 1:
                        request.user.bonus_balance += 10  # Бонус покупателю
                        request.user.save()
                        friend.bonus_balance += 10  # Бонус владельцу промокода
                        friend.save()
                        # Фиксируем активацию
                        PromoCodeActivation.objects.create(
                            user=request.user,
                            promo_code=promo
                        )

            except PromoCode.DoesNotExist:
                pass

        return redirect('core:confirm_purchase', purchase_id=purchase.id)

    except Purchase.DoesNotExist:
        return render(request, 'core/step3.html', {
            'error': 'Ошибка покупки: покупка не найдена.',
            'robux': purchase.robux_amount if 'purchase' in locals() else 0,
            'price': float(purchase.price) if 'purchase' in locals() else 0,
            'place_id': place_id if 'place_id' in locals() else '',
            'place_name': purchase.place_name if 'purchase' in locals() else '',
            'purchase_id': purchase_id,
            'promo_code': promo_code,
            'gamepasses': gamepasses if 'gamepasses' in locals() else [],
            'gamepass_price': round(purchase.price / Decimal('0.7')) if 'purchase' in locals() else 0,
            'instruction': (
                "1. Выберите существующий GamePass или создайте новый с ценой {} Robux.\n"
                "2. Опубликуйте и активируйте 'For Sale'.\n"
                "3. Нажмите 'Проверить', затем 'Оплатить'.".format(
                    round(purchase.price / Decimal('0.7')) if 'purchase' in locals() else 0
                )
            ),
        })


@login_required
def confirm_purchase(request, purchase_id):
    purchase = get_object_or_404(Purchase, id=purchase_id, user=request.user)
    context = {
        'purchase': purchase,
        'robux': purchase.robux_amount,
        'price': float(purchase.price),
        'gamepass_id': purchase.gamepass_id,
        'gamepass_price': purchase.gamepass_price,
        'purchase_id': purchase.id,
        'promo_code': purchase.promo_code_used,
        'place_id': purchase.place_id,
        'place_name': purchase.place_name,
    }
    return render(request, 'core/confirm.html', context)


@login_required
def withdraw_bonus(request):
    if request.user.bonus_balance < 50:
        return render(request, 'core/withdraw.html', {'error': 'Недостаточно средств для вывода.'})
    if request.method == 'POST':
        return redirect('core:withdraw_step2')
    return render(request, 'core/withdraw.html', {'bonus_balance': request.user.bonus_balance})


@login_required
def withdraw_step2(request):
    if request.user.bonus_balance < 50:
        return render(request, 'core/withdraw.html', {'error': 'Недостаточно средств для вывода.'})
    places = get_roblox_places(request.user.roblox_nick)
    if not places:
        return render(request, 'core/withdraw_step2.html',
                      {'error': 'У вас нет доступных мест.', 'bonus_balance': request.user.bonus_balance})
    return render(request, 'core/withdraw_step2.html', {'places': places, 'bonus_balance': request.user.bonus_balance})


@login_required
@require_POST
def withdraw_step3(request):
    bonus_balance = float(request.POST.get('bonus_balance', 0))
    place_id = request.POST.get('place_id')
    place_link = request.POST.get('place_link', '')
    action = request.POST.get('action')
    selected_gamepass_id = request.POST.get('gamepass_id')

    if not place_id:
        return render(request, 'core/withdraw_step2.html', {
            'error': 'Пожалуйста, выберите место.',
            'places': get_roblox_places(request.user.roblox_nick),
            'bonus_balance': bonus_balance
        })

    universe_id = get_universe_id(place_id)
    if not universe_id:
        return render(request, 'core/withdraw_step3.html', {
            'error': 'Не удалось получить universe_id для выбранного места.',
            'bonus_balance': bonus_balance,
            'place_id': place_id
        })

    gamepasses = get_gamepasses(universe_id)
    requested_price = round(bonus_balance / 0.7)
    if action == 'check' and not selected_gamepass_id and gamepasses:
        return render(request, 'core/withdraw_step3.html', {
            'error': 'Выберите существующий GamePass или создайте новый.',
            'bonus_balance': bonus_balance,
            'place_id': place_id,
            'place_link': place_link,
            'gamepasses': gamepasses,
            'requested_price': requested_price,
            'instruction': (
                "1. Выберите существующий GamePass или создайте новый с ценой {} Robux.\n"
                "2. Опубликуйте и активируйте 'For Sale'.\n"
                "3. Нажмите 'Проверить', затем 'Подтвердить'.".format(requested_price)
            ),
        })

    if action == 'check' and selected_gamepass_id:
        matching_gamepass = next((gp for gp in gamepasses if str(gp['id']) == selected_gamepass_id), None)
        if not matching_gamepass or matching_gamepass['price'] != requested_price:
            return render(request, 'core/withdraw_step3.html', {
                'error': f'Выбранный GamePass должен стоить {requested_price} Robux.',
                'bonus_balance': bonus_balance,
                'place_id': place_id,
                'place_link': place_link,
                'gamepasses': gamepasses,
                'requested_price': requested_price,
                'instruction': (
                    "1. Выберите существующий GamePass или создайте новый с ценой {} Robux.\n"
                    "2. Опубликуйте и активируйте 'For Sale'.\n"
                    "3. Нажмите 'Проверить', затем 'Подтвердить'.".format(requested_price)
                ),
            })

    context = {
        'bonus_balance': bonus_balance,
        'place_id': place_id,
        'place_link': place_link,
        'gamepasses': gamepasses,
        'requested_price': requested_price,
        'matching_gamepass': next((gp for gp in gamepasses if str(gp['id']) == selected_gamepass_id),
                                  None) if selected_gamepass_id else None,
        'instruction': (
            "1. Выберите существующий GamePass или создайте новый с ценой {} Robux.\n"
            "2. Опубликуйте и активируйте 'For Sale'.\n"
            "3. Нажмите 'Проверить', затем 'Подтвердить'.".format(requested_price)
        ),
    }
    return render(request, 'core/withdraw_step3.html', context)


@login_required
@require_POST
def withdraw_confirm(request):
    bonus_balance = float(request.POST.get('bonus_balance', 0))
    place_id = request.POST.get('place_id')
    gamepass_id = request.POST.get('gamepass_id')

    if not gamepass_id:
        return render(request, 'core/withdraw_step3.html', {
            'error': 'Пожалуйста, выберите GamePass.',
            'bonus_balance': bonus_balance,
            'place_id': place_id,
            'gamepasses': get_gamepasses(get_universe_id(place_id))
        })

    withdrawal = Withdrawal.objects.create(
        user=request.user,
        amount=bonus_balance,
        gamepass_id=gamepass_id,
        status='pending'
    )

    request.user.bonus_balance -= bonus_balance
    request.user.save()

    return render(request, 'core/withdraw_confirm.html', {
        'bonus_balance': bonus_balance,
        'place_id': place_id,
        'gamepass_id': gamepass_id,
        'withdrawal_id': withdrawal.id,
        'status': 'success',
        'message': 'Заявка на вывод создана.',
    })


@login_required
@require_POST
def social_bonus(request, social):
    last_bonus_time = request.session.get(f'last_social_bonus_{social}', timezone.now() - timezone.timedelta(hours=1))
    if (timezone.now() - last_bonus_time).total_seconds() < 5:
        return JsonResponse({'success': False, 'message': 'Подождите 5 секунд.'})
    request.user.bonus_balance += 5
    request.user.save()
    request.session[f'last_social_bonus_{social}'] = timezone.now()
    return JsonResponse({'success': True})


def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            roblox_nick = form.cleaned_data['roblox_nick']
            user_id, avatar_url = get_roblox_user_data(roblox_nick)
            if user_id is None:
                return render(request, 'core/login.html', {'form': form, 'error': 'Неверный ник Roblox.'})
            user, created = CustomUser.objects.get_or_create(
                roblox_user_id=user_id,
                defaults={'roblox_nick': roblox_nick}
            )
            if created and not user.promo_code:
                user.promo_code = CustomUser.objects.generate_promo_code()
                user.save()
            if avatar_url and (created or not user.avatar_url):
                user.avatar_url = avatar_url
                user.save()
            login(request, user)
            return redirect('/')
        return render(request, 'core/login.html', {'form': form, 'error': 'Неверный ник Roblox.'})
    else:
        form = LoginForm()
    return render(request, 'core/login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('/')


def get_roblox_user_data(nick):
    try:
        r = requests.post(
            "https://users.roblox.com/v1/usernames/users",
            json={"usernames": [nick], "excludeBannedUsers": True},
            timeout=5
        )
        r.raise_for_status()
        user_data = r.json().get('data', [])
        if not user_data:
            return None, None
        user_data = user_data[0]
        user_id = user_data['id']
        headshot = requests.get(
            f"https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={user_id}&size=150x150&format=Png"
        )
        headshot.raise_for_status()
        avatar_url = headshot.json()['data'][0]['imageUrl']
        return user_id, avatar_url
    except Exception:
        return None, None


def get_roblox_places(nick):
    try:
        user_id, _ = get_roblox_user_data(nick)
        if not user_id:
            return []
        headers = {'x-api-key': settings.ROBLOX_API_KEY}
        url = f"https://games.roblox.com/v2/users/{user_id}/games"
        params = {"sortOrder": "Asc", "limit": 50}
        places = requests.get(url, headers=headers, params=params, timeout=5)
        places.raise_for_status()
        games = places.json().get('data', [])
        if not games:
            return []
        result = []
        for game in games:
            place_id = str(game.get('rootPlace', {}).get('id'))
            if not place_id:
                continue
            result.append({
                'rootPlace': {
                    'id': place_id,
                    'name': game.get('name', 'Без названия')
                }
            })
        return result
    except Exception:
        return []


def get_universe_id(place_id):
    try:
        r = requests.get(f"https://apis.roblox.com/universes/v1/places/{place_id}/universe")
        r.raise_for_status()
        return r.json().get("universeId")
    except Exception:
        return None


def get_gamepasses(universe_id):
    try:
        r = requests.get(f"https://games.roblox.com/v1/games/{universe_id}/game-passes?limit=100")
        r.raise_for_status()
        data = r.json().get("data", [])
        if not data:
            return []
        return [{'id': gp['id'], 'price': gp['price'], 'name': gp.get('name', f'GamePass {gp["id"]}')} for gp in data]
    except Exception:
        return []
