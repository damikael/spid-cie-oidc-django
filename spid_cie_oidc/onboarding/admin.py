from django.contrib import admin
from django.contrib import messages
from django.db import IntegrityError

from .models import OnBoardingRegistration
from spid_cie_oidc.authority.models import FederationDescendant


@admin.register(OnBoardingRegistration)
class OnBoardingRegistrationAdmin(admin.ModelAdmin):

    @admin.action(description='enable descendant')
    def make_published(modeladmin, request, queryset):
        entity_onboarded = queryset[0]
        name = entity_onboarded.organization_name
        sub = entity_onboarded.url_entity
        jwks = entity_onboarded.public_jwks
        _type = entity_onboarded.type

        try:
            FederationDescendant.objects.create(
                name = name,
                sub = sub,
                type = _type,
                jwks = jwks,
                is_active = True,
            )
        except IntegrityError:
            messages.error(request, f"Already exists a descendant with subject: {sub}" )

    list_display = (
        "organization_name",
        "url_entity",
        "type",
        "authn_buttons_page_url",
        "public_jwks",
    )
    actions = [make_published]
