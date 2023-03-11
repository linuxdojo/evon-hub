from fastapi import FastAPI
from pydantic import BaseModel, Field

from evon.selfhosted_shim.ec2_metadata import EC2Metadata

app = FastAPI()
ec2_md = EC2Metadata()


class RegistrationData(BaseModel):
    subnet_key: str = Field(alias="subnet-key")
    domain_prefix: str = Field(alias="domain-prefix")


@app.get("/latest/dynamic/instance-identity/document")
def read_ec2_metadata():
    return ec2_md.get_metadata_json()


@app.get("/latest/meta-data/iam/security-credentials")
def read_security_credentials():
    return ec2_md.get_security_credentials()


@app.get("/latest/dynamic/instance-identity/signature")
def read_signature():
    return ec2_md.get_signature()


@app.get("/latest/meta-data/public-ipv4")
def read_pub_ipv4():
    return ec2_md.get_pub_ipv4()
