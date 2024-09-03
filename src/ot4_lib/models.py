import os
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


def default_wid_generator_factory(class_name):
    return partial(make_wid, to_snake_case(class_name))


class WidMetaclass(type(models.Model)):
    @classmethod
    def is_abstract(cls, attrs):
        meta = attrs.get("Meta")
        return bool(meta and hasattr(meta, "abstract") and meta.abstract)

    def __new__(cls, name, bases, attrs):
        if not cls.is_abstract(attrs):
            default_wid_generator = default_wid_generator_factory(name)
            attrs["wid"] = models.CharField(
                max_length=len(default_wid_generator()) + 100,
                unique=True,
                default=default_wid_generator,
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

    def save(self, **kwargs):
        self.update_modified = kwargs.pop(
            "update_modified",
            getattr(self, "update_modified", True),
        )
        super().save(**kwargs)


class SafeImageFieldFile(models.ImageField.attr_class):
    @property
    def url(self):
        # Check if the file exists (i.e., it's not None and has a file associated)
        if self and self.name:
            return super().url
        return None


class SafeImageField(models.ImageField):
    attr_class = SafeImageFieldFile


class SafeFileFieldFile(models.FileField.attr_class):
    @property
    def url(self):
        # Check if the file exists (i.e., it's not None and has a file associated)
        if self and self.name:
            return super().url
        return None


class SafeFileField(models.FileField):
    attr_class = SafeFileFieldFile


def up(template, instance, filename):
    # Get the base name and extension using os.path.splitext
    basename, ext = os.path.splitext(filename)
    ext = ext.lstrip(".")  # Remove the dot from the extension
    wid = instance.wid

    context = dict(
        basename=basename,
        filename=filename,
        ext=ext,
        wid=wid,
        instance=instance,
    )

    # Format the template with context
    return template.format(**context)
