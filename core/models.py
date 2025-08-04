from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
import random
import string


class CustomUserManager(BaseUserManager):
    def generate_promo_code(self):
        characters = string.ascii_letters + string.digits
        while True:
            code = ''.join(random.choices(characters, k=6))
            if not CustomUser.objects.filter(promo_code=code).exists():
                return code

    def create_user(self, roblox_nick, roblox_user_id, avatar_url=None, password=None, **extra_fields):
        if not roblox_nick:
            raise ValueError("The roblox_nick field must be set")
        if not roblox_user_id:
            raise ValueError("The roblox_user_id field must be set")

        user = self.model(
            roblox_nick=roblox_nick,
            roblox_user_id=roblox_user_id,
            avatar_url=avatar_url or "https://example.com/default-avatar.png",
            **extra_fields
        )
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        if not user.promo_code:
            while True:
                code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
                if not CustomUser.objects.filter(promo_code=code).exists():
                    user.promo_code = code
                    break

            PromoCode.objects.create(
                code=code,
                promo_type='friend',
                created_by=user
            )

        user.save()
        return user

    def create_superuser(self, roblox_nick, roblox_user_id, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self.create_user(roblox_nick, roblox_user_id, password=password, **extra_fields)


class CustomUser(AbstractBaseUser, PermissionsMixin):
    roblox_nick = models.CharField(max_length=150, unique=True)
    roblox_user_id = models.BigIntegerField(unique=True)
    avatar_url = models.URLField(blank=True, null=True)
    promo_code = models.CharField(max_length=6, unique=True, blank=True, null=True)
    bonus_balance = models.IntegerField(default=0, verbose_name="Бонусный баланс")
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    vk_subscribed = models.BooleanField(default=False, verbose_name="Подписан на VK")
    discord_joined = models.BooleanField(default=False, verbose_name="Вступил в Discord")
    telegram_joined = models.BooleanField(default=False, verbose_name="Вступил в Telegram")
    active_promo_code = models.ForeignKey(
        'PromoCode',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='activated_by_users'
    )

    def can_activate_promo(self, promo_code):
        return not PromoCodeActivation.objects.filter(
            user=self,
            promo_code=promo_code
        ).exists()

    objects = CustomUserManager()

    USERNAME_FIELD = 'roblox_nick'
    REQUIRED_FIELDS = ['roblox_user_id']

    def __str__(self):
        return self.roblox_nick


class Purchase(models.Model):
    STATUS_CHOICES = [
        ('pending', 'В ожидании'),
        ('completed', 'Получено'),
        ('declined', 'Отклонено'),
    ]
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    robux_amount = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    gamepass_id = models.CharField(max_length=100, blank=True, null=True)
    gamepass_price = models.IntegerField(blank=True, null=True)
    place_id = models.CharField(max_length=50, blank=True, null=True)
    place_name = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    promo_code_used = models.CharField(max_length=6, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)


class Withdrawal(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    amount = models.FloatField(default=0.0)
    gamepass_id = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(max_length=20, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Withdrawal {self.id} by {self.user.roblox_nick}"


class CurrencyRate(models.Model):
    currency = models.CharField(max_length=3, choices=[('RUB', 'Ruble'), ('USD', 'Dollar')], unique=True)
    rate = models.DecimalField(max_digits=10, decimal_places=4)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.currency} = {self.rate} per Robux"


class PromoCode(models.Model):
    PROMO_TYPES = [
        ('friend', 'Дружеский'),
        ('general', 'Общий'),
    ]

    code = models.CharField(max_length=20, unique=True)
    promo_type = models.CharField(max_length=10, choices=PROMO_TYPES)
    bonus_amount = models.IntegerField(default=10)
    created_by = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='created_promo_codes'
    )
    is_active = models.BooleanField(default=True)
    valid_until = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.code} ({self.get_promo_type_display()})"


class PromoCodeActivation(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    promo_code = models.ForeignKey(PromoCode, on_delete=models.CASCADE)
    activated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [['user', 'promo_code']]