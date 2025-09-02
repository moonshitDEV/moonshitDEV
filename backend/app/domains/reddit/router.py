from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from ...security.deps import require_user_or_hmac
from .services import (
    reddit_me,
    reddit_listing,
    subreddit_about,
    subreddit_rules,
    subreddit_wiki,
    reddit_search,
    reddit_comments,
    reddit_submit,
    reddit_comment,
    reddit_edit,
    reddit_delete,
    reddit_vote,
    reddit_save,
    reddit_unsave,
    mod_approve,
    mod_remove,
    mod_lock,
    mod_unlock,
    mod_sticky,
    mod_distinguish,
    mod_ban,
    mod_unban,
    flair_user,
    flair_link,
    set_suggested_sort,
    modqueue_list,
    ops_registry,
    proxy_dispatch,
    inbox_list,
    send_message,
)


router = APIRouter(prefix="/reddit", tags=["reddit"])  # container
read_dep = Depends(require_user_or_hmac(["reddit:read"]))
write_dep = Depends(require_user_or_hmac(["reddit:write"]))
read = APIRouter(dependencies=[read_dep])
write = APIRouter(dependencies=[write_dep])


@read.get("/{profile}/me")
def get_me(profile: str):
    return reddit_me(profile)


@read.get("/{profile}/subs")
def get_subs(profile: str, modonly: bool = False, after: Optional[str] = None, limit: int = 25):
    return reddit_listing(profile, sub=None, sort="subs", after=after, limit=limit, modonly=modonly)


@read.get("/{profile}/r/{sub}/about")
def get_sub_about(profile: str, sub: str):
    return subreddit_about(profile, sub)


@read.get("/{profile}/r/{sub}/rules")
def get_sub_rules(profile: str, sub: str):
    return subreddit_rules(profile, sub)


@read.get("/{profile}/r/{sub}/wiki/{path}")
def get_sub_wiki(profile: str, sub: str, path: str):
    return subreddit_wiki(profile, sub, path)


@read.get("/{profile}/r/{sub}/{sort}")
def get_listing(profile: str, sub: str, sort: str, after: Optional[str] = None, limit: int = 25, t: Optional[str] = None):
    return reddit_listing(profile, sub=sub, sort=sort, after=after, limit=limit, time_filter=t)


@read.get("/{profile}/search")
def search(profile: str, q: str, sub: Optional[str] = None, type: Optional[str] = None):
    return reddit_search(profile, q=q, sub=sub, type=type)


@read.get("/{profile}/comments/{post_id}")
def comments(profile: str, post_id: str):
    return reddit_comments(profile, post_id)


# Write
@write.post("/{profile}/r/{sub}/submit")
def submit(profile: str, sub: str, kind: str, title: str, text: Optional[str] = None, url: Optional[str] = None, nsfw: Optional[bool] = None, spoiler: Optional[bool] = None, flair: Optional[str] = None):
    return reddit_submit(profile, sub=sub, kind=kind, title=title, text=text, url=url, nsfw=nsfw, spoiler=spoiler, flair=flair)


@write.post("/{profile}/comment")
def comment(profile: str, parent_id: str, text: str):
    return reddit_comment(profile, parent_id=parent_id, text=text)


@write.post("/{profile}/edit")
def edit(profile: str, thing_id: str, text: str):
    return reddit_edit(profile, thing_id=thing_id, text=text)


@write.post("/{profile}/delete")
def delete(profile: str, thing_id: str):
    return reddit_delete(profile, thing_id=thing_id)


@write.post("/{profile}/vote")
def vote(profile: str, thing_id: str, dir: int):
    return reddit_vote(profile, thing_id=thing_id, dir=dir)


@write.post("/{profile}/save")
def save(profile: str, thing_id: str):
    return reddit_save(profile, thing_id)


@write.post("/{profile}/unsave")
def unsave(profile: str, thing_id: str):
    return reddit_unsave(profile, thing_id)


# Moderation queues
@read.get("/{profile}/r/{sub}/modqueue")
def modqueue(profile: str, sub: str):
    return modqueue_list(profile, sub, queue="modqueue")


@read.get("/{profile}/r/{sub}/reports")
def reports(profile: str, sub: str):
    return modqueue_list(profile, sub, queue="reports")


@read.get("/{profile}/r/{sub}/spam")
def spam(profile: str, sub: str):
    return modqueue_list(profile, sub, queue="spam")


@read.get("/{profile}/r/{sub}/edited")
def edited(profile: str, sub: str):
    return modqueue_list(profile, sub, queue="edited")


@read.get("/{profile}/r/{sub}/unmoderated")
def unmoderated(profile: str, sub: str):
    return modqueue_list(profile, sub, queue="unmoderated")


@read.get("/{profile}/r/{sub}/mod/log")
def modlog(profile: str, sub: str):
    return modqueue_list(profile, sub, queue="modlog")


# Moderation actions
@write.post("/{profile}/mod/approve")
def approve(profile: str, thing_id: str):
    return mod_approve(profile, thing_id)


@write.post("/{profile}/mod/remove")
def remove(profile: str, thing_id: str, spam: bool = False):
    return mod_remove(profile, thing_id, spam)


@write.post("/{profile}/mod/lock")
def lock(profile: str, thing_id: str):
    return mod_lock(profile, thing_id)


@write.post("/{profile}/mod/unlock")
def unlock(profile: str, thing_id: str):
    return mod_unlock(profile, thing_id)


@write.post("/{profile}/mod/sticky")
def sticky(profile: str, thing_id: str, state: bool):
    return mod_sticky(profile, thing_id, state)


@write.post("/{profile}/mod/distinguish")
def distinguish(profile: str, thing_id: str, how: str):
    return mod_distinguish(profile, thing_id, how)


@write.post("/{profile}/mod/ban")
def ban(profile: str, user: str, sub: str, reason: str | None = None, days: int | None = None):
    return mod_ban(profile, user, sub, reason, days)


@write.post("/{profile}/mod/unban")
def unban(profile: str, user: str, sub: str):
    return mod_unban(profile, user, sub)


@write.post("/{profile}/r/{sub}/flair/user")
def flair_u(profile: str, sub: str, user: str, flair_text: str | None = None, flair_template_id: str | None = None):
    return flair_user(profile, sub, user, flair_text, flair_template_id)


@write.post("/{profile}/r/{sub}/flair/link")
def flair_l(profile: str, sub: str, thing_id: str, flair_text: str | None = None, flair_template_id: str | None = None):
    return flair_link(profile, sub, thing_id, flair_text, flair_template_id)


@write.post("/{profile}/r/{sub}/set_suggested_sort")
def set_sort(profile: str, sub: str, thing_id: str, sort: str):
    return set_suggested_sort(profile, sub, thing_id, sort)


# Messaging
@read.get("/{profile}/inbox")
def inbox(profile: str, type: str = "all", after: Optional[str] = None, limit: int = 25):
    return inbox_list(profile, type, after, limit)


@write.post("/{profile}/message")
def message(profile: str, to: str, subject: str, text: str):
    return send_message(profile, to, subject, text)


# Proxy allowlist
@read.get("/ops")
def list_ops():
    return ops_registry()


@read.get("/ops/{namespace}/{operation}")
def get_op(namespace: str, operation: str):
    reg = ops_registry()
    return reg.get("schemas", {}).get(f"{namespace}.{operation}") or {"detail": "Not found"}


@write.post("/{profile}/proxy")
def proxy(profile: str, namespace: str, operation: str, params: dict):
    return proxy_dispatch(profile, namespace, operation, params)

# Mount grouped routers under /reddit
router.include_router(read)
router.include_router(write)
