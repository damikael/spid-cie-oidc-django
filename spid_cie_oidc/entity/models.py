import json
import logging
import uuid

from cryptojwt.jwk.jwk import key_from_jwk_dict
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext as _
from spid_cie_oidc.entity.abstract_models import TimeStampedModel
from spid_cie_oidc.entity.jwks import (
    create_jwk,
    private_pem_from_jwk,
    public_pem_from_jwk,
    serialize_rsa_key
)
from spid_cie_oidc.entity.jwtse import create_jws
from spid_cie_oidc.entity.settings import (
    ENTITY_STATUS,
    ENTITY_TYPE_LEAFS,
    ENTITY_TYPES,
    FEDERATION_DEFAULT_EXP
)
from spid_cie_oidc.entity.statements import EntityConfiguration
from spid_cie_oidc.entity.utils import exp_from_now, iat_now
from spid_cie_oidc.entity.validators import (
    validate_entity_metadata,
    validate_metadata_algs
)

logger = logging.getLogger(__name__)


def is_leaf(statement_metadata):
    for _typ in ENTITY_TYPE_LEAFS:
        if _typ in statement_metadata:
            return True


class FederationEntityConfiguration(TimeStampedModel):
    """
    Federation Authority configuration.

    # TODO: validate metadata upon type field
    """

    def _create_jwks():
        return [create_jwk()]

    uuid = models.UUIDField(
        blank=False, null=False, default=uuid.uuid4, unique=True, editable=False
    )
    sub = models.URLField(
        max_length=255,
        blank=False,
        null=False,
        help_text=_(
            "URL that identifies this Entity in the Federation. "
            "This value and iss are the same in the Entity Configuration."
        ),
    )
    default_exp = models.PositiveIntegerField(
        default=FEDERATION_DEFAULT_EXP,
        help_text=_("how many minutes from now() an issued statement must expire"),
    )
    default_signature_alg = models.CharField(
        max_length=16,
        default="RS256",
        blank=False,
        null=False,
        help_text=_("default signature algorithm, eg: RS256"),
    )
    authority_hints = models.JSONField(
        blank=True,
        null=False,
        help_text=_("only required if this Entity is an intermediary or leaf."),
        default=list,
    )
    jwks = models.JSONField(
        blank=False,
        null=False,
        help_text=_("a list of private keys"),
        default=_create_jwks,
    )
    trust_marks = models.JSONField(
        blank=True,
        help_text=_("which trust marks MUST be exposed in its entity configuration"),
        default=list,
    )
    trust_marks_issuers = models.JSONField(
        blank=True,
        help_text=_(
            "Only usable for Trust Anchors and intermediates. "
            "Which issuers are allowed to issue trust marks for the descendants. "
            'Example: {"https://www.spid.gov.it/certification/rp": '
            '["https://registry.spid.agid.gov.it", "https://intermediary.spid.it"],'
            '"https://sgd.aa.it/onboarding": ["https://sgd.aa.it", ]}'
        ),
        default=dict,
    )
    entity_type = models.CharField(
        max_length=33,
        blank=True,
        default="openid_relying_party",
        choices=[(i, i) for i in ENTITY_TYPES],
        help_text=_("OpenID Connect Federation entity type"),
    )
    metadata = models.JSONField(
        blank=False,
        null=False,
        help_text=_(
            "federation_entity metadata, eg: "
            '{"federation_entity": { ... },'
            '"openid_provider": { ... },'
            '"openid_relying_party": { ... },'
            '"oauth_resource": { ... }'
            "}"
        ),
        default=dict,
        validators=[
            validate_entity_metadata,
            validate_metadata_algs
        ],
    )
    constraints = models.JSONField(
        blank=True,
        help_text=_(
            """
{
  "naming_constraints": {
    "permitted": [
      "https://.example.com"
    ],
    "excluded": [
      "https://east.example.com"
    ]
  },
  "max_path_length": 2
}
"""
        ),
        default=dict,
        # TODO
        # validators=[validate_entity_metadata,]
    )
    is_active = models.BooleanField(
        default=False,
        help_text=_(
            "If this configuration is active. "
            "At least one configuration must be active"
        ),
    )

    class Meta:
        verbose_name = "Federation Entity Configuration"
        verbose_name_plural = "Federation Entity Configurations"

    @classmethod
    def get_active_conf(cls):
        """
        returns the first available active acsia engine configuration found
        """
        return cls.objects.filter(is_active=True).first()

    @property
    def public_jwks(self):
        res = []
        for i in self.jwks:
            skey = serialize_rsa_key(key_from_jwk_dict(i).public_key())
            skey["kid"] = i["kid"]
            res.append(skey)
        return res

    @property
    def pems_as_dict(self):
        res = {}
        for i in self.jwks:
            res[i["kid"]] = {
                "private": private_pem_from_jwk(i),
                "public": public_pem_from_jwk(i),
            }
        return res

    @property
    def pems_as_json(self):
        return json.dumps(self.pems_as_dict, indent=2)

    @property
    def kids(self) -> list:
        return [i["kid"] for i in self.jwks]

    @property
    def type(self) -> list:
        return [i for i in self.metadata.keys()]

    @property
    def is_leaf(self):
        return is_leaf(self.metadata)

    @property
    def entity_configuration_as_dict(self):
        conf = {
            "exp": exp_from_now(self.default_exp),
            "iat": iat_now(),
            "iss": self.sub,
            "sub": self.sub,
            "jwks": {"keys": self.public_jwks},
            "metadata": self.metadata,
        }

        if self.trust_marks_issuers:
            conf["trust_marks_issuers"] = self.trust_marks_issuers

        if self.trust_marks:
            conf["trust_marks"] = self.trust_marks

        if self.constraints:
            conf["constraints"] = self.constraints

        if self.authority_hints:
            conf["authority_hints"] = self.authority_hints
        elif self.is_leaf:
            _msg = f"Entity {self.sub} is a leaf and requires authority_hints valued"
            logger.error(_msg)

        return conf

    @property
    def entity_configuration_as_json(self):
        return json.dumps(self.entity_configuration_as_dict)

    @property
    def entity_configuration_as_jws(self, **kwargs):
        return create_jws(
            self.entity_configuration_as_dict,
            self.jwks[0],
            alg=self.default_signature_alg,
            typ="entity-statement+jwt",
            **kwargs,
        )

    def __str__(self):
        return "{} [{}]".format(self.sub, "active" if self.is_active else "--")


class FetchedEntityStatement(TimeStampedModel):
    """
    Entity Statement acquired by a third party
    """

    iss = models.URLField(
        max_length=255,
        blank=False,
        help_text=_(
            "URL that identifies the issuer of this statement in the Federation. "
        ),
    )
    sub = models.URLField(
        max_length=255,
        blank=False,
        help_text=_("URL that identifies this Entity in the Federation. "),
    )
    exp = models.DateTimeField()
    iat = models.DateTimeField()

    statement = models.JSONField(
        blank=False, null=False, help_text=_("Entity statement"), default=dict
    )
    jwt = models.CharField(max_length=2048)

    class Meta:
        verbose_name = "Fetched Entity Statement"
        verbose_name_plural = "Fetched Entity Statement"

    def get_entity_configuration_as_obj(self):
        return EntityConfiguration(self.jwt)

    @property
    def is_expired(self):
        return self.exp <= timezone.localtime()

    def __str__(self):
        return f"{self.sub} issued by {self.iss}"


class TrustChain(TimeStampedModel):
    """
    Federation Trust Chain
    """

    sub = models.URLField(
        max_length=255,
        blank=False,
        help_text=_("URL that identifies this Entity in the Federation. "),
    )
    trust_anchor = models.ForeignKey(FetchedEntityStatement, on_delete=models.CASCADE)
    type = models.CharField(
        max_length=33,
        blank=True,
        default="openid_provider",
        choices=[(i, i) for i in ENTITY_TYPES],
        help_text=_("OpenID Connect Federation entity type"),
    )
    exp = models.DateTimeField()
    iat = models.DateTimeField(auto_now_add=True)
    chain = models.JSONField(
        blank=True,
        help_text=_(
            "A list of entity statements collected during the metadata discovery"
        ),
        default=list,
    )
    metadata = models.JSONField(
        blank=True,
        null=True,
        help_text=_(
            "The final metadata applied with the metadata policy built over the chain"
        ),
        default=dict,
    )
    trust_marks = models.JSONField(
        blank=True, help_text=_("verified trust marks"), default=list
    )
    parties_involved = models.JSONField(
        blank=True,
        help_text=_("subjects involved in the metadata discovery"),
        default=list,
    )
    status = models.CharField(
        max_length=33,
        default="unreachable",
        help_text=_("Status of this trust chain, on each update."),
        choices=[(i, i) for i in list(ENTITY_STATUS.keys())],
    )
    log = models.TextField(blank=True, help_text=_("status log"), default="")
    processing_start = models.DateTimeField(
        help_text=_(
            "When the metadata discovery started for this Trust Chain. "
            "It should prevent concurrent processing for the same sub/type."
        ),
        default=timezone.localtime,
    )
    is_active = models.BooleanField(
        default=True,
        help_text=_("If you need to disable the trust to this subject, uncheck this"),
    )

    class Meta:
        verbose_name = "Trust Chain"
        verbose_name_plural = "Trust Chains"
        unique_together = ("sub", "type", "trust_anchor")

    @property
    def subject(self):
        return self.sub

    @property
    def is_expired(self):
        return self.exp <= timezone.localtime()

    @property
    def iat_as_timestamp(self):
        return int(self.iat.timestamp())

    @property
    def exp_as_timestamp(self):
        return int(self.exp.timestamp())

    @property
    def is_valid(self):
        return self.is_active and ENTITY_STATUS[self.status]

    # TODO: property is_expired

    def __str__(self):
        return "{} [{}] [{}]".format(self.sub, self.type, self.is_valid)
