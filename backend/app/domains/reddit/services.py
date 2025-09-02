from __future__ import annotations

# pip install praw httpx feedparser
import concurrent.futures
from typing import Any, Optional

import httpx
import feedparser
import praw

from ...settings import get_settings


_executor = concurrent.futures.ThreadPoolExecutor(max_workers=8)


def _profile_env(prefix: str) -> dict[str, str]:
    import os

    up = prefix.upper()
    return {
        "client_id": os.environ.get(f"REDDIT_{up}_CLIENT_ID", ""),
        "client_secret": os.environ.get(f"REDDIT_{up}_CLIENT_SECRET", ""),
        "refresh_token": os.environ.get(f"REDDIT_{up}_REFRESH_TOKEN", ""),
        "user_agent": os.environ.get(f"REDDIT_{up}_USER_AGENT", f"moonshit.dev/{up}") or f"moonshit.dev/{up}",
        "username": os.environ.get(f"REDDIT_{up}_USERNAME", ""),
        "password": os.environ.get(f"REDDIT_{up}_PASSWORD", ""),
    }


def _reddit(profile: str) -> praw.Reddit:
    cfg = _profile_env(profile)
    if not cfg["client_id"] or not cfg["client_secret"]:
        raise RuntimeError("Reddit client id/secret missing for profile")
    if cfg["refresh_token"]:
        return praw.Reddit(
            client_id=cfg["client_id"],
            client_secret=cfg["client_secret"],
            refresh_token=cfg["refresh_token"],
            user_agent=cfg["user_agent"],
        )
    if cfg["username"] and cfg["password"]:
        return praw.Reddit(
            client_id=cfg["client_id"],
            client_secret=cfg["client_secret"],
            username=cfg["username"],
            password=cfg["password"],
            user_agent=cfg["user_agent"],
        )
    raise RuntimeError("Reddit creds must provide either refresh token or username/password")


def reddit_me(profile: str) -> dict:
    def _work():
        me = _reddit(profile).user.me()
        return {"name": me.name, "id": me.id}

    return _executor.submit(_work).result()


def subreddit_about(profile: str, sub: str) -> dict:
    def _work():
        s = _reddit(profile).subreddit(sub)
        return {"display_name": s.display_name, "title": s.title, "subscribers": s.subscribers, "over18": s.over18}

    return _executor.submit(_work).result()


def subreddit_rules(profile: str, sub: str) -> dict:
    def _work():
        rules = _reddit(profile).subreddit(sub).rules()
        return {"rules": [r.short_name for r in rules]}

    return _executor.submit(_work).result()


def subreddit_wiki(profile: str, sub: str, path: str) -> dict:
    def _work():
        page = _reddit(profile).subreddit(sub).wiki[path]
        return {"content_md": page.content_md}

    return _executor.submit(_work).result()


def reddit_listing(profile: str, sub: Optional[str], sort: str, after: Optional[str], limit: int, time_filter: Optional[str] = None, modonly: bool = False) -> dict:
    def _work():
        if sort == "subs":
            me = _reddit(profile).user.me()
            subs = list(me.moderator_subreddits(limit=None) if modonly else me.subreddits(limit=None))
            return {"subs": [s.display_name for s in subs]}
        s = _reddit(profile).subreddit(sub)
        listing = []
        gen = None
        if sort == "new":
            gen = s.new(limit=limit)
        elif sort == "hot":
            gen = s.hot(limit=limit)
        elif sort == "top":
            gen = s.top(limit=limit, time_filter=time_filter or "day")
        elif sort == "rising":
            gen = s.rising()
        elif sort == "controversial":
            gen = s.controversial(limit=limit, time_filter=time_filter or "day")
        else:
            raise ValueError("bad sort")
        for p in gen:
            listing.append({
                "id": p.id,
                "name": p.name,
                "title": p.title,
                "author": str(getattr(p, 'author', None)) if getattr(p, 'author', None) else None,
                "created_utc": p.created_utc,
                "score": p.score,
                "num_comments": p.num_comments,
                "url": p.url,
                "permalink": p.permalink,
                "over_18": p.over_18,
            })
        return {"items": listing}

    try:
        return _executor.submit(_work).result()
    except Exception:
        # RSS fallback (read-only)
        if sub:
            url = f"https://www.reddit.com/r/{sub}/.rss"
            r = httpx.get(url, headers={"User-Agent": "moonshit.dev/rss"}, timeout=10)
            feed = feedparser.parse(r.text)
            items = [{"title": e.get("title"), "link": e.get("link"), "published": e.get("published")} for e in feed.entries]
            return {"items": items, "readonly": True}
        raise


def reddit_search(profile: str, q: str, sub: Optional[str], type: Optional[str]):
    def _work():
        sr = _reddit(profile).subreddit(sub) if sub else _reddit(profile).subreddit("all")
        results = sr.search(q, syntax="lucene", limit=25)
        return {"items": [{"id": p.id, "title": p.title, "author": str(p.author) if p.author else None, "permalink": p.permalink} for p in results]}

    return _executor.submit(_work).result()


def reddit_comments(profile: str, post_id: str):
    def _work():
        s = _reddit(profile).submission(id=post_id)
        s.comments.replace_more(limit=0)
        def flatten(cs):
            out = []
            for c in cs:
                out.append({"id": c.id, "author": str(c.author) if c.author else None, "body": c.body, "score": getattr(c, 'score', 0)})
                if getattr(c, 'replies', None):
                    out.extend(flatten(c.replies))
            return out
        return {"post": {"id": s.id, "title": s.title}, "comments": flatten(s.comments)}

    return _executor.submit(_work).result()


def reddit_submit(profile: str, sub: str, kind: str, title: str, text: Optional[str], url: Optional[str], nsfw: Optional[bool], spoiler: Optional[bool], flair: Optional[str]):
    def _work():
        sr = _reddit(profile).subreddit(sub)
        if kind == "self":
            res = sr.submit(title=title, selftext=text or "")
        elif kind == "link":
            res = sr.submit(title=title, url=url or "")
        else:
            res = sr.submit(title=title, selftext=text or "")
        if nsfw:
            res.mod.nsfw()
        if spoiler:
            res.mod.spoiler()
        return {"thing_id": res.name, "id": res.id, "permalink": res.permalink}

    return _executor.submit(_work).result()


def reddit_comment(profile: str, parent_id: str, text: str):
    def _work():
        if parent_id.startswith("t3_"):
            subm = _reddit(profile).submission(id=parent_id.split("_", 1)[1])
            c = subm.reply(text)
            return {"id": c.id}
        else:
            c = _reddit(profile).comment(id=parent_id.split("_", 1)[1]).reply(text)
            return {"id": c.id}

    return _executor.submit(_work).result()


def reddit_edit(profile: str, thing_id: str, text: str):
    def _work():
        if thing_id.startswith("t1_"):
            c = _reddit(profile).comment(id=thing_id.split("_", 1)[1])
            c.edit(text)
        else:
            s = _reddit(profile).submission(id=thing_id.split("_", 1)[1])
            s.edit(text)
        return {"ok": True}

    return _executor.submit(_work).result()


def reddit_delete(profile: str, thing_id: str):
    def _work():
        if thing_id.startswith("t1_"):
            _reddit(profile).comment(id=thing_id.split("_", 1)[1]).delete()
        else:
            _reddit(profile).submission(id=thing_id.split("_", 1)[1]).delete()
        return {"ok": True}

    return _executor.submit(_work).result()


def reddit_vote(profile: str, thing_id: str, dir: int):
    def _work():
        obj = _reddit(profile).submission(id=thing_id.split("_", 1)[1]) if thing_id.startswith("t3_") else _reddit(profile).comment(id=thing_id.split("_", 1)[1])
        if dir == 1:
            obj.upvote()
        elif dir == -1:
            obj.downvote()
        else:
            obj.clear_vote()
        return {"ok": True}

    return _executor.submit(_work).result()


def reddit_save(profile: str, thing_id: str):
    def _work():
        obj = _reddit(profile).submission(id=thing_id.split("_", 1)[1]) if thing_id.startswith("t3_") else _reddit(profile).comment(id=thing_id.split("_", 1)[1])
        obj.save()
        return {"ok": True}

    return _executor.submit(_work).result()


def reddit_unsave(profile: str, thing_id: str):
    def _work():
        obj = _reddit(profile).submission(id=thing_id.split("_", 1)[1]) if thing_id.startswith("t3_") else _reddit(profile).comment(id=thing_id.split("_", 1)[1])
        obj.unsave()
        return {"ok": True}

    return _executor.submit(_work).result()


def modqueue_list(profile: str, sub: str, queue: str):
    def _work():
        s = _reddit(profile).subreddit(sub)
        if queue == "modqueue":
            it = s.mod.modqueue(limit=50)
        elif queue == "reports":
            it = s.mod.reports(limit=50)
        elif queue == "spam":
            it = s.mod.spam(limit=50)
        elif queue == "edited":
            it = s.mod.edited(limit=50)
        elif queue == "unmoderated":
            it = s.mod.unmoderated(limit=50)
        elif queue == "modlog":
            it = s.mod.log(limit=50)
        else:
            it = []
        return {"items": [getattr(i, 'id', None) for i in it]}

    return _executor.submit(_work).result()


def mod_approve(profile: str, thing_id: str):
    def _work():
        obj = _reddit(profile).submission(id=thing_id.split("_", 1)[1]) if thing_id.startswith("t3_") else _reddit(profile).comment(id=thing_id.split("_", 1)[1])
        obj.mod.approve()
        return {"ok": True}

    return _executor.submit(_work).result()


def mod_remove(profile: str, thing_id: str, spam: bool):
    def _work():
        obj = _reddit(profile).submission(id=thing_id.split("_", 1)[1]) if thing_id.startswith("t3_") else _reddit(profile).comment(id=thing_id.split("_", 1)[1])
        obj.mod.remove(spam=spam)
        return {"ok": True}

    return _executor.submit(_work).result()


def mod_lock(profile: str, thing_id: str):
    def _work():
        _reddit(profile).submission(id=thing_id.split("_", 1)[1]).mod.lock()
        return {"ok": True}

    return _executor.submit(_work).result()


def mod_unlock(profile: str, thing_id: str):
    def _work():
        _reddit(profile).submission(id=thing_id.split("_", 1)[1]).mod.unlock()
        return {"ok": True}

    return _executor.submit(_work).result()


def mod_sticky(profile: str, thing_id: str, state: bool):
    def _work():
        s = _reddit(profile).submission(id=thing_id.split("_", 1)[1])
        if state:
            s.mod.sticky()
        else:
            s.mod.sticky(state=False)
        return {"ok": True}

    return _executor.submit(_work).result()


def mod_distinguish(profile: str, thing_id: str, how: str):
    def _work():
        s = _reddit(profile).submission(id=thing_id.split("_", 1)[1])
        s.mod.distinguish(how)
        return {"ok": True}

    return _executor.submit(_work).result()


def mod_ban(profile: str, user: str, sub: str, reason: Optional[str], days: Optional[int]):
    def _work():
        _reddit(profile).subreddit(sub).banned.add(user, reason=reason or "", duration=days)
        return {"ok": True}

    return _executor.submit(_work).result()


def mod_unban(profile: str, user: str, sub: str):
    def _work():
        _reddit(profile).subreddit(sub).banned.remove(user)
        return {"ok": True}

    return _executor.submit(_work).result()


def flair_user(profile: str, sub: str, user: str, flair_text: Optional[str], flair_template_id: Optional[str]):
    def _work():
        _reddit(profile).subreddit(sub).flair.set(user, text=flair_text, flair_template_id=flair_template_id)
        return {"ok": True}

    return _executor.submit(_work).result()


def flair_link(profile: str, sub: str, thing_id: str, flair_text: Optional[str], flair_template_id: Optional[str]):
    def _work():
        _reddit(profile).submission(id=thing_id.split("_", 1)[1]).flair.select(flair_template_id, text=flair_text)
        return {"ok": True}

    return _executor.submit(_work).result()


def set_suggested_sort(profile: str, sub: str, thing_id: str, sort: str):
    def _work():
        _reddit(profile).submission(id=thing_id.split("_", 1)[1]).mod.suggested_sort(sort)
        return {"ok": True}

    return _executor.submit(_work).result()


def inbox_list(profile: str, type: str, after: Optional[str], limit: int):
    def _work():
        u = _reddit(profile).inbox
        if type == "unread":
            it = u.unread(limit=limit)
        else:
            it = u.all(limit=limit)
        return {"items": [getattr(m, 'subject', None) for m in it]}

    return _executor.submit(_work).result()


def send_message(profile: str, to: str, subject: str, text: str):
    def _work():
        _reddit(profile).redditor(to).message(subject, text)
        return {"ok": True}

    return _executor.submit(_work).result()


def ops_registry() -> dict:
    # Minimal skeleton of allowlisted operations and param schemas
    schemas = {
        "subreddit.about": {"params": {"sub": {"type": "string"}}},
        "subreddit.rules": {"params": {"sub": {"type": "string"}}},
        "listing.new": {"params": {"sub": {"type": "string"}, "limit": {"type": "integer"}}},
    }
    return {"namespaces": ["subreddit", "listing"], "schemas": schemas}


def proxy_dispatch(profile: str, namespace: str, operation: str, params: dict) -> Any:
    key = f"{namespace}.{operation}"
    reg = ops_registry().get("schemas", {})
    if key not in reg:
        return {"detail": "Operation not allowlisted"}
    if key == "subreddit.about":
        return subreddit_about(profile, params.get("sub"))
    if key == "subreddit.rules":
        return subreddit_rules(profile, params.get("sub"))
    if key == "listing.new":
        return reddit_listing(profile, sub=params.get("sub"), sort="new", after=None, limit=params.get("limit", 25))
    return {"detail": "Not implemented"}
