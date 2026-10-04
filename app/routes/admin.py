"""The operator's pages (specs/LEARN.md §6.1, §6.1.1): adding and deleting
learners, and their time spent."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse, Response

from ..admin import require_admin
from ..i18n import t
from ..store import AccountExists, Store
from ..web import course_lang, course_ui, get_store, templates

# Unpublished: nothing outside /admin links here. Every route sits on this router, whose
# dependency enforces the admin password; none looks at the current learner.

router = APIRouter(prefix="/admin", dependencies=[Depends(require_admin)])
NOINDEX = {"X-Robots-Tag": "noindex, nofollow"}


def _admin_page(request: Request, name: str, context: dict) -> Response:
    response = templates.TemplateResponse(
        request=request, name=name, context={**course_lang(request), **context}
    )
    response.headers.update(NOINDEX)
    return response


def _admin_redirect(url: str) -> Response:
    return RedirectResponse(url, status_code=303, headers=NOINDEX)


def _learners_page(request: Request, store: Store, error: str | None = None, name: str = "") -> Response:
    return _admin_page(
        request,
        "admin_learners.html",
        {"accounts": store.accounts(), "activity": store.activity_summary(), "error": error, "name": name},
    )


@router.get("")
def admin_index(request: Request):
    return _admin_page(request, "admin_index.html", {})


@router.get("/learners")
def admin_learners(request: Request, store: Store = Depends(get_store)):
    return _learners_page(request, store)


@router.post("/learners")
def admin_add_learner(request: Request, display_name: str = Form(""), store: Store = Depends(get_store)):
    ui = course_ui(request)
    try:
        store.create_account(display_name)
    except AccountExists as e:
        # Refused with a message on the same page, not an error page (§6.1).
        return _learners_page(request, store, t(ui, "learner_exists", name=str(e)), display_name)
    except ValueError:
        return _learners_page(request, store, t(ui, "learner_invalid_name"), display_name)
    return _admin_redirect("/admin/learners")


@router.get("/learners/{account_id}/delete")
def admin_confirm_delete(request: Request, account_id: str, store: Store = Depends(get_store)):
    account = store.get_account(account_id)
    if account is None:
        return _admin_redirect("/admin/learners")
    return _admin_page(
        request, "admin_delete.html", {"account": account, "summary": store.account_summary(account_id)}
    )


@router.post("/learners/{account_id}/delete")
def admin_delete(account_id: str, store: Store = Depends(get_store)):
    store.delete_account(account_id)
    return _admin_redirect("/admin/learners")
