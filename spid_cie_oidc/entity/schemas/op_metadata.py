from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, HttpUrl, validator

from .jwks import JwksCie, JwksSpid

JWKS_URI_CIE = "https://registry.cie.gov.it/.well-known/jwks.json"


class ScopeSupported(str, Enum):
    openid = "openid"
    offline_access = "offline_access"
    profile = "profile"
    email = "email"


class ResponseModesSupported(str, Enum):
    form_post = ("form_post",)
    query = "query"


class GrantTypeSupported(str, Enum):
    refresh_token = "refresh_token"  # nosec - B105
    authorization_code = "authorization_code"


class AcrValuesSupportedSpid(str, Enum):
    spid_l1 = "https://www.spid.gov.it/SpidL1"
    spid_l2 = "https://www.spid.gov.it/SpidL2"
    spid_l3 = "https://www.spid.gov.it/SpidL3"


class AcrValuesSupportedCie(str, Enum):
    cie_l1 = "CIE_L1"
    cie_l2 = "CIE_L2"
    cie_l3 = "CIE_L3"


class SigningAlgValuesSupported(str, Enum):
    es256 = "ES256"
    es384 = "ES384"
    es512 = "ES512"
    rs256 = "RS256"
    rs384 = "RS384"
    rs512 = "RS512"
    # TODO: to be confirmed
    # ps256 = "PS256"
    # ps384 = "PS384"
    # ps512 = "PS512"


class EncryptionAlgValuesSupported(str, Enum):
    rsa_oaep = "RSA-OAEP"
    ras_oaep_256 = "RSA-OAEP-256"
    ecdh_es = "ECDH-ES"
    ecdh_es_a128kw = "ECDH-ES+A128KW"
    ecdh_es_a192kw = "ECDH-ES+A192KW"
    ecdh_es_a256kw = "ECDH-ES+A256KW"


class EncryptionEncValuesSupported(str, Enum):
    a128cbc_hs256 = "A128CBC-HS256"
    a192cbc_hs384 = "A192CBC-HS384"
    a256cbc_hs512 = "A256CBC-HS512"
    a128gcm = "A128GCM"
    a192gcm = "A192GCM"
    a256gcm = "A256GCM"


class ClaimsSupported(str, Enum):
    given_name = "given_name"
    family_name = "family_name"
    email = "email"
    email_verified = "email_verified"
    gender = "gender"
    birthdate = "birthdate"
    phone_number = "phone_number"
    phone_number_verified = "phone_number_verified"
    place_of_birth = "place_of_birth"
    address = "address"
    document_details = "document_details"
    https_attributes_eid_gov_it_e_delivery_service = (
        "https://attributes.eid.gov.it/e_delivery_service"
    )
    https_attributes_eid_gov_it_fiscal_number = (
        "https://attributes.eid.gov.it/fiscal_number"
    )
    https_attributes_eid_gov_it_idANPR = "https://attributes.eid.gov.it/idANPR"
    https_attributes_eid_gov_it_physical_phone_number = (
        "https://attributes.eid.gov.it/physical_phone_number"
    )


class OPMetadata(BaseModel):
    issuer: HttpUrl
    authorization_endpoint: HttpUrl
    token_endpoint: HttpUrl
    userinfo_endpoint: HttpUrl
    introspection_endpoint: HttpUrl
    revocation_endpoint: HttpUrl
    token_endpoint_auth_signing_alg_values_supported: List[SigningAlgValuesSupported]
    id_token_encryption_alg_values_supported: List[EncryptionAlgValuesSupported]
    id_token_encryption_enc_values_supported: List[EncryptionEncValuesSupported]
    userinfo_encryption_alg_values_supported: List[EncryptionAlgValuesSupported]
    userinfo_encryption_enc_values_supported: List[EncryptionEncValuesSupported]
    request_object_encryption_alg_values_supported: List[EncryptionAlgValuesSupported]
    request_object_encryption_enc_values_supported: List[EncryptionEncValuesSupported]
    id_token_signing_alg_values_supported: List[SigningAlgValuesSupported]
    userinfo_signing_alg_values_supported: List[SigningAlgValuesSupported]
    request_object_signing_alg_values_supported: List[SigningAlgValuesSupported]
    token_endpoint_auth_methods_supported = ["private_key_jwt"]
    subject_types_supported = ["pairwise"]
    request_parameter_supported = True


class OPMetadataCie(OPMetadata):
    jwks: Optional[JwksCie]
    jwks_uri: Optional[HttpUrl]
    scopes_supported: List[ScopeSupported]
    response_types_supported = ["code"]
    response_modes_supported: List[ResponseModesSupported]
    grant_types_supported: List[GrantTypeSupported]
    acr_values_supported: List[AcrValuesSupportedCie]
    claims_supported: List[ClaimsSupported]
    claims_parameter_supported = True
    tls_client_certificate_bound_access_tokens = True
    authorization_response_iss_parameter_supported = True

    @validator("jwks_uri")
    def validate_jwks_uri(cls, jwks_uri, values):
        if jwks_uri != JWKS_URI_CIE:
            raise ValueError("jwks_uri no correct")
        jwks = values.get("jwks")
        if jwks_uri and jwks:
            raise ValueError("jwks MUST NOT indicate")


class OPMetadataSpid(OPMetadata):
    jwks: Optional[JwksSpid]
    jwks_uri: Optional[HttpUrl]
    # TODO: Could be specified in multiple languages
    op_name: str
    # TODO: Could be specified in multiple languages
    op_uri: str
    acr_values_supported: List[AcrValuesSupportedSpid]

    @validator("jwks_uri")
    def validate_jwks_uri(cls, jwks_uri, values):
        if jwks_uri != JWKS_URI_CIE:
            raise ValueError("jwks no correct")
        jwks = values.get("jwks")
        if jwks_uri and jwks:
            raise ValueError("jwks MUST NOT indicate")
