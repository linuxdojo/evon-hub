from fastapi import FastAPI
from pydantic import BaseModel, Field

from ec2_metadata import EC2Metadata
from evon_api import EvonAPI

app = FastAPI()
ec2_md = EC2Metadata()
evon_api = EvonAPI()


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


@app.get("/zone/update/{version}")
def get_update(version):
    return evon_api.get_update()


@app.post("/zone/register")
def register(data: RegistrationData):
    data = data.dict()
    return evon_api.register(data)


@app.delete("/zone/deregister")
def deregister(data, request):
    return evon_api.deregister(data)


@app.get("/zone/records")
def get_records():
    return evon_api.get_records()


@app.put("/zone/records")
def set_records(changes, request):
    return evon_api.set_records(changes)
