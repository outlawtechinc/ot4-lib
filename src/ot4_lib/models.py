from functools import partial

from django.db import models
from django_extensions.db.fields import CreationDateTimeField
from django_extensions.db.fields import ModificationDateTimeField

from .shortuuidx import uuid as suuid


def parse_wid(wid: str) -> (str, str):
    if "_" not in wid:
        return wid, ""
    prefix, wid = wid.split("_", maxsplit=1)
    return prefix, wid


def make_wid(prefix: str, wid: str | None = None) -> str:
    if not wid:
        wid = suuid()
    if "_" in wid and prefix:
        old_prefix, wid = wid.split("_", maxsplit=1)
    if not prefix:
        prefix = ""
    return f"{prefix}_{wid}"


def to_snake_case(name):
    return "".join(["_" + i.lower() if i.isupper() else i for i in name]).lstrip("_")


def default_wid_generator(class_name):
    return partial(make_wid, to_snake_case(class_name))


class WidMetaclass(type(models.Model)):
    @classmethod
    def is_abstract(cls, attrs):
        meta = attrs.get("Meta")
        return bool(meta and hasattr(meta, "abstract") and meta.abstract)

    def __new__(cls, name, bases, attrs):
        if not cls.is_abstract(attrs):
            attrs["wid"] = models.CharField(
                max_length=100,
                unique=True,
                default=default_wid_generator(name),
                editable=False,
            )

        new_class = super().__new__(cls, name, bases, attrs)
        if cls.is_abstract(attrs):
            new_class._meta.abstract = True

        return new_class


class WidModel(models.Model, metaclass=WidMetaclass):
    created = CreationDateTimeField(
        editable=False,
        db_index=True,
        auto_now_add=True,
        blank=True,
    )
    modified = ModificationDateTimeField(
        auto_now=True,
        db_index=True,
        blank=True,
    )
    is_active = models.BooleanField(default=True)
    extra = models.JSONField(default=dict, blank=True, null=True)

    class Meta:
        get_latest_by = "modified"
        abstract = True

    def __str__(self):
        return self.wid

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "wid" not in kwargs:
            self.wid = self._meta.get_field("wid").default()

    def save(self, **kwargs):
        self.update_modified = kwargs.pop(
            "update_modified",
            getattr(self, "update_modified", True),
        )
        super().save(**kwargs)
