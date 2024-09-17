from cacheops.invalidation import invalidate_all, invalidate_model, invalidate_obj
from django.db.models import Model
from django.db.models.base import ModelBase
from django.conf import settings
from typing import Union, List


def invalidate_cacheops(
    something: Union[None, Model, ModelBase, List[Model], List[ModelBase]] = None
):
    if not getattr(settings, "CACHEOPS_ENABLED", False):
        return

    if something is None:
        invalidate_all()
        return

    if not isinstance(something, (list, tuple)):
        items = [something]
    else:
        items = something

    for item in items:
        if isinstance(item, ModelBase):
            # It's a model class
            invalidate_model(item)
        elif isinstance(item, Model):
            # It's a model instance
            invalidate_obj(item)
        else:
            raise ValueError("Invalid argument passed to invalidate_cacheops")
