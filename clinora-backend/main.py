"""
main.py — minimal app composition entrypoint.
"""

from dotenv import load_dotenv

load_dotenv()

from core.app_factory import create_app
from api.routers.auth import router as auth_router
from api.routers.patients import router as patients_router
from api.routers.session_flow import router as session_flow_router
from api.routers.session_flow import session_update
from api.routers.session_manage import router as session_manage_router
from api.routers.system import router as system_router

app = create_app()
app.include_router(system_router)
app.include_router(auth_router)
app.include_router(patients_router)
app.include_router(session_flow_router)
app.include_router(session_manage_router)

# Compatibility attributes for older tests/extensions. Interviewing now runs
# through app.interview_graph and these hooks are not used by the router.
call_interviewer = None
classify_safety = None
call_agent_commentary = None
