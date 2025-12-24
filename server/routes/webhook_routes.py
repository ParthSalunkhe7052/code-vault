"""
Webhook routes for CodeVault API.
Extracted from main.py for modularity.
"""

import json
import time
import secrets
import hashlib
import hmac
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
import httpx

from utils import get_current_user, utc_now
from database import get_db, release_db
from models import WebhookCreateRequest
from middleware.tier_enforcement import requires_feature

router = APIRouter(prefix="/api/v1/webhooks", tags=["Webhooks"])

WEBHOOK_EVENTS = [
    "license.created",
    "license.validated", 
    "license.revoked",
    "license.expired",
    "hwid.bound",
    "hwid.reset",
    "compilation.started",
    "compilation.completed",
    "compilation.failed"
]


class WebhookUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    url: Optional[str] = Field(None, max_length=500)
    events: Optional[List[str]] = None
    secret: Optional[str] = Field(None, max_length=100)
    is_active: Optional[bool] = None


async def trigger_webhook(user_id: str, event: str, payload: dict):
    """
    Send webhook notifications for an event.
    Fetches all active webhooks for the user subscribed to this event,
    sends HTTP POST requests, and logs delivery results.
    """
    conn = await get_db()
    try:
        rows = await conn.fetch("""
            SELECT id, url, secret, events FROM webhooks 
            WHERE user_id = $1 AND is_active = TRUE
        """, user_id)
        
        for webhook in rows:
            events = webhook['events']
            if isinstance(events, str):
                try:
                    events = json.loads(events)
                except Exception:
                    events = []
            
            if event not in events:
                continue
            
            webhook_id = webhook['id']
            url = webhook['url']
            secret = webhook['secret']
            
            webhook_payload = {
                "event": event,
                "timestamp": utc_now().isoformat(),
                "data": payload
            }
            
            headers = {"Content-Type": "application/json"}
            if secret:
                payload_str = json.dumps(webhook_payload, sort_keys=True)
                signature = hmac.new(secret.encode(), payload_str.encode(), hashlib.sha256).hexdigest()
                headers["X-Webhook-Signature"] = signature
            
            start_time = time.time()
            delivery_id = secrets.token_hex(16)
            
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.post(url, json=webhook_payload, headers=headers)
                    delivery_time_ms = int((time.time() - start_time) * 1000)
                    
                    success = 200 <= response.status_code < 300
                    await conn.execute("""
                        INSERT INTO webhook_deliveries (id, webhook_id, event_type, payload, response_status, response_body, delivery_time_ms, success, created_at)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW())
                    """, delivery_id, webhook_id, event, json.dumps(webhook_payload), response.status_code, 
                        response.text[:1000] if response.text else None, delivery_time_ms, success)
                    
                    if success:
                        await conn.execute("""
                            UPDATE webhooks SET last_triggered_at = NOW(), failure_count = 0 WHERE id = $1
                        """, webhook_id)
                    else:
                        await conn.execute("""
                            UPDATE webhooks SET last_triggered_at = NOW(), failure_count = failure_count + 1 WHERE id = $1
                        """, webhook_id)
                        
            except Exception as e:
                delivery_time_ms = int((time.time() - start_time) * 1000)
                await conn.execute("""
                    INSERT INTO webhook_deliveries (id, webhook_id, event_type, payload, response_status, response_body, delivery_time_ms, success, created_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW())
                """, delivery_id, webhook_id, event, json.dumps(webhook_payload), 0, str(e)[:1000], delivery_time_ms, False)
                
                await conn.execute("""
                    UPDATE webhooks SET failure_count = failure_count + 1 WHERE id = $1
                """, webhook_id)
                print(f"[Webhook] Failed to deliver {event} to {url}: {e}")
                
    except Exception as e:
        print(f"[Webhook] Error triggering webhooks for {event}: {e}")
    finally:
        await release_db(conn)


@router.get("")
async def list_webhooks(user: dict = Depends(get_current_user)):
    """List all webhooks for the current user."""
    conn = await get_db()
    try:
        rows = await conn.fetch("""
            SELECT id, name, url, events, is_active, last_triggered_at, failure_count, created_at
            FROM webhooks WHERE user_id = $1 ORDER BY created_at DESC
        """, user['id'])
        
        result = []
        for w in rows:
            events = w['events']
            if isinstance(events, str):
                try:
                    events = json.loads(events)
                except Exception:
                    events = []
            result.append({
                "id": w['id'],
                "name": w['name'],
                "url": w['url'],
                "events": events,
                "is_active": bool(w['is_active']),
                "last_triggered_at": w['last_triggered_at'].isoformat() if w['last_triggered_at'] else None,
                "failure_count": w['failure_count'] or 0,
                "created_at": w['created_at'].isoformat() if w['created_at'] else None
            })
        return result
    finally:
        await release_db(conn)


@router.post("")
@requires_feature('webhooks')
async def create_webhook(data: WebhookCreateRequest, user: dict = Depends(get_current_user)):
    """Create a new webhook."""
    invalid_events = [e for e in data.events if e not in WEBHOOK_EVENTS]
    if invalid_events:
        raise HTTPException(status_code=400, detail=f"Invalid events: {invalid_events}")
    
    if not data.url.startswith(('http://', 'https://')):
        raise HTTPException(status_code=400, detail="Webhook URL must start with http:// or https://")
    
    conn = await get_db()
    try:
        webhook_id = secrets.token_hex(16)
        events_json = json.dumps(data.events)
        
        await conn.execute("""
            INSERT INTO webhooks (id, user_id, name, url, secret, events, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, NOW())
        """, webhook_id, user['id'], data.name, data.url, data.secret, events_json)
        
        return {
            "id": webhook_id,
            "name": data.name,
            "url": data.url,
            "events": data.events,
            "is_active": True,
            "last_triggered_at": None,
            "failure_count": 0,
            "created_at": utc_now().isoformat()
        }
    finally:
        await release_db(conn)


@router.get("/{webhook_id}")
async def get_webhook(webhook_id: str, user: dict = Depends(get_current_user)):
    """Get a specific webhook."""
    conn = await get_db()
    try:
        row = await conn.fetchrow("""
            SELECT id, name, url, events, secret, is_active, last_triggered_at, failure_count, created_at
            FROM webhooks WHERE id = $1 AND user_id = $2
        """, webhook_id, user['id'])
        
        if not row:
            raise HTTPException(status_code=404, detail="Webhook not found")
        
        events = row['events']
        if isinstance(events, str):
            try:
                events = json.loads(events)
            except Exception:
                events = []
        
        return {
            "id": row['id'],
            "name": row['name'],
            "url": row['url'],
            "events": events,
            "secret": row['secret'],
            "is_active": bool(row['is_active']),
            "last_triggered_at": row['last_triggered_at'].isoformat() if row['last_triggered_at'] else None,
            "failure_count": row['failure_count'] or 0,
            "created_at": row['created_at'].isoformat() if row['created_at'] else None
        }
    finally:
        await release_db(conn)


@router.put("/{webhook_id}")
async def update_webhook(webhook_id: str, data: WebhookUpdateRequest, user: dict = Depends(get_current_user)):
    """Update a webhook."""
    conn = await get_db()
    try:
        exists = await conn.fetchrow("SELECT id FROM webhooks WHERE id = $1 AND user_id = $2", webhook_id, user['id'])
        if not exists:
            raise HTTPException(status_code=404, detail="Webhook not found")
        
        updates = []
        params = []
        param_count = 1
        
        if data.name is not None:
            updates.append(f"name = ${param_count}")
            params.append(data.name)
            param_count += 1
        if data.url is not None:
            if not data.url.startswith(('http://', 'https://')):
                raise HTTPException(status_code=400, detail="Webhook URL must start with http:// or https://")
            updates.append(f"url = ${param_count}")
            params.append(data.url)
            param_count += 1
        if data.events is not None:
            invalid_events = [e for e in data.events if e not in WEBHOOK_EVENTS]
            if invalid_events:
                raise HTTPException(status_code=400, detail=f"Invalid events: {invalid_events}")
            updates.append(f"events = ${param_count}")
            params.append(json.dumps(data.events))
            param_count += 1
        if data.secret is not None:
            updates.append(f"secret = ${param_count}")
            params.append(data.secret)
            param_count += 1
        if data.is_active is not None:
            updates.append(f"is_active = ${param_count}")
            params.append(data.is_active)
            param_count += 1
        
        if updates:
            updates.append("updated_at = NOW()")
            params.append(webhook_id)
            await conn.execute(f"UPDATE webhooks SET {', '.join(updates)} WHERE id = ${param_count}", *params)
        
        return await get_webhook(webhook_id, user)
    finally:
        await release_db(conn)


@router.delete("/{webhook_id}")
async def delete_webhook(webhook_id: str, user: dict = Depends(get_current_user)):
    """Delete a webhook."""
    conn = await get_db()
    try:
        exists = await conn.fetchrow("SELECT id FROM webhooks WHERE id = $1 AND user_id = $2", webhook_id, user['id'])
        if not exists:
            raise HTTPException(status_code=404, detail="Webhook not found")
        
        await conn.execute("DELETE FROM webhooks WHERE id = $1", webhook_id)
        return {"status": "deleted"}
    finally:
        await release_db(conn)


@router.get("/{webhook_id}/deliveries")
async def get_webhook_deliveries(webhook_id: str, limit: int = 50, user: dict = Depends(get_current_user)):
    """Get delivery history for a webhook."""
    conn = await get_db()
    try:
        exists = await conn.fetchrow("SELECT id FROM webhooks WHERE id = $1 AND user_id = $2", webhook_id, user['id'])
        if not exists:
            raise HTTPException(status_code=404, detail="Webhook not found")
        
        rows = await conn.fetch("""
            SELECT id, event_type, payload, response_status, response_body, delivery_time_ms, success, created_at
            FROM webhook_deliveries WHERE webhook_id = $1
            ORDER BY created_at DESC LIMIT $2
        """, webhook_id, limit)
        
        return [{
            "id": row['id'],
            "event_type": row['event_type'],
            "payload": json.loads(row['payload']) if row['payload'] else None,
            "response_status": row['response_status'],
            "response_body": row['response_body'],
            "delivery_time_ms": row['delivery_time_ms'],
            "success": row['success'],
            "created_at": row['created_at'].isoformat() if row['created_at'] else None
        } for row in rows]
    finally:
        await release_db(conn)


@router.post("/{webhook_id}/test")
async def test_webhook(webhook_id: str, user: dict = Depends(get_current_user)):
    """Test a webhook by sending a test payload."""
    conn = await get_db()
    try:
        webhook = await conn.fetchrow("SELECT id, url, secret FROM webhooks WHERE id = $1 AND user_id = $2", webhook_id, user['id'])
        if not webhook:
            raise HTTPException(status_code=404, detail="Webhook not found")
        
        url = webhook['url']
        secret = webhook['secret']
        
        test_payload = {
            "event": "test",
            "timestamp": utc_now().isoformat(),
            "data": {
                "message": "This is a test webhook from CodeVault",
                "webhook_id": webhook_id
            }
        }
        
        headers = {"Content-Type": "application/json"}
        if secret:
            payload_str = json.dumps(test_payload, sort_keys=True)
            signature = hmac.new(secret.encode(), payload_str.encode(), hashlib.sha256).hexdigest()
            headers["X-Webhook-Signature"] = signature
        
        start_time = time.time()
        delivery_id = secrets.token_hex(16)
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, json=test_payload, headers=headers)
                delivery_time_ms = int((time.time() - start_time) * 1000)
                success = 200 <= response.status_code < 300
                
                await conn.execute("""
                    INSERT INTO webhook_deliveries (id, webhook_id, event_type, payload, response_status, response_body, delivery_time_ms, success, created_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW())
                """, delivery_id, webhook_id, "test", json.dumps(test_payload), response.status_code, 
                    response.text[:1000] if response.text else None, delivery_time_ms, success)
                
                await conn.execute("UPDATE webhooks SET last_triggered_at = NOW(), failure_count = 0 WHERE id = $1", webhook_id)
                
                if success:
                    return {"status": "success", "message": f"Test webhook sent successfully! Response: {response.status_code}", "delivery_time_ms": delivery_time_ms}
                else:
                    return {"status": "error", "message": f"Webhook returned non-2xx status: {response.status_code}", "delivery_time_ms": delivery_time_ms}
                    
        except Exception as e:
            delivery_time_ms = int((time.time() - start_time) * 1000)
            await conn.execute("""
                INSERT INTO webhook_deliveries (id, webhook_id, event_type, payload, response_status, response_body, delivery_time_ms, success, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW())
            """, delivery_id, webhook_id, "test", json.dumps(test_payload), 0, str(e)[:1000], delivery_time_ms, False)
            
            await conn.execute("UPDATE webhooks SET failure_count = failure_count + 1 WHERE id = $1", webhook_id)
            # Security: Log error details server-side, return generic message to client
            import logging
            from utils import sanitize_log_message
            logging.error(f"[Webhook Test] Failed to send webhook {webhook_id}: {sanitize_log_message(str(e))}")
            raise HTTPException(status_code=500, detail="Failed to send test webhook. Please check the URL and try again.")
    finally:
        await release_db(conn)


@router.get("/events/list")
async def get_webhook_events():
    """Get list of available webhook events with descriptions."""
    descriptions = {
        "license.created": "Triggered when a new license is created",
        "license.validated": "Triggered when a license is successfully validated",
        "license.revoked": "Triggered when a license is revoked",
        "license.expired": "Triggered when a license expires during validation",
        "hwid.bound": "Triggered when a new hardware ID is bound to a license",
        "hwid.reset": "Triggered when hardware bindings are reset for a license",
        "compilation.started": "Triggered when a compilation job starts",
        "compilation.completed": "Triggered when a compilation job completes successfully",
        "compilation.failed": "Triggered when a compilation job fails"
    }
    return {
        "events": WEBHOOK_EVENTS,
        "descriptions": descriptions
    }
