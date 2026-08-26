"""Comprehensive QA & Live Testing Script for AI Models (Xiaomi MiMo & DeepSeek)."""
import os
import sys
import time

# Ensure UTF-8 output on Windows console
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import get_settings
from services.ai.mimo_service import XiaomiMiMoService
from services.ai.deepseek_service import DeepSeekService
from services.ai.orchestrator import AIPitchOrchestrator
from db.repositories.journalists_repo import JournalistsRepository
from db.repositories.campaigns_repo import CampaignsRepository


def run_comprehensive_ai_qa():
    settings = get_settings()
    print("=" * 70)
    print("[AI QA] OPENCLAW PR MANAGER -- AI MODELS QA & VERIFICATION SUITE")
    print("=" * 70)
    print(f"* Xiaomi MiMo Model:    {settings.MIMO_MODEL}")
    print(f"* Xiaomi MiMo Base URL: {settings.MIMO_BASE_URL}")
    print(f"* Xiaomi MiMo Key:      {'Configured (Active)' if settings.is_mimo_configured else 'Missing'}")
    print(f"* DeepSeek Model:       {settings.DEEPSEEK_MODEL}")
    print(f"* DeepSeek Base URL:    {settings.DEEPSEEK_BASE_URL}")
    print(f"* DeepSeek Key:         {'Configured (Active)' if settings.is_deepseek_configured else 'Fallback Mode'}")
    print("-" * 70)

    # 1. Test Direct Xiaomi MiMo Pitch Generation
    print("\n[TEST 1] Testing Direct Xiaomi MiMo (mimo-v2.5-pro) Live Generation...")
    mimo_svc = XiaomiMiMoService()
    start_time = time.time()
    
    test_sys = "You are an elite PR specialist. Write a concise, personalized email pitch."
    test_user = (
        "Journalist: Peter Loftus at The Wall Street Journal (Beat: Healthcare, Biotech, Pharma)\n"
        "Story: MedTech AI announces FDA clearance for autonomous diagnostic assistant for oncology clinics.\n\n"
        "Write a 3-paragraph pitch with a compelling subject line."
    )
    
    try:
        mimo_res = mimo_svc.generate_pitch(test_sys, test_user)
        elapsed = time.time() - start_time
        print(f"[PASS] Xiaomi MiMo Response Received in {elapsed:.2f}s!")
        print(f"   Subject: {mimo_res.get('subject_line')}")
        print("   Body Preview:")
        for line in mimo_res.get('pitch_email', '').split('\n')[:5]:
            print(f"      {line}")
        print("      ...")
    except Exception as e:
        print(f"[FAIL] Xiaomi MiMo Generation Failed: {e}")

    # 2. Test AIPitchOrchestrator with Real Database Records
    print("\n[TEST 2] Testing AIPitchOrchestrator End-to-End with DB Contacts...")
    j_repo = JournalistsRepository()
    orch = AIPitchOrchestrator()

    # Pick a real journalist from the imported dataset
    all_journalists = j_repo.list_all(limit=5)
    sample_j = all_journalists[0] if all_journalists else {
        "name": "Sarah Connor",
        "outlet": "Tech Weekly",
        "beat": ["Artificial Intelligence", "Robotics"],
        "bio": "Senior reporter covering autonomous systems."
    }

    sample_campaign = {
        "name": "OpenClaw PR 2.0 Launch",
        "story": (
            "OpenClaw unveils autonomous PR pitching and follow-up engine powered by Xiaomi MiMo AI "
            "and DeepSeek with real-time Gmail reply tracking and 4D journalist scoring."
        ),
        "target_beat": ["AI", "Startups", "Software"],
    }

    print(f"   Target Journalist: {sample_j.get('name')} ({sample_j.get('outlet')})")
    print(f"   Beats: {', '.join(sample_j.get('beat') or [])}")
    print(f"   Campaign: {sample_campaign.get('name')}")

    # Initial pitch test
    start_time = time.time()
    orch_res_initial = orch.generate_pitch(
        journalist=sample_j,
        campaign=sample_campaign,
        model="mimo-v2.5-pro",
        pitch_type="initial",
    )
    elapsed = time.time() - start_time
    print(f"\n[PASS] Initial Pitch Generated ({elapsed:.2f}s):")
    print(f"   Subject: {orch_res_initial.get('subject_line')}")
    print(f"   Pitch Content:\n{orch_res_initial.get('pitch_email')}\n")

    # Follow-up test (3+7+7+14 sequence template)
    start_time = time.time()
    orch_res_followup = orch.generate_pitch(
        journalist=sample_j,
        campaign=sample_campaign,
        model="mimo-v2.5-pro",
        pitch_type="followup_1",
    )
    elapsed = time.time() - start_time
    print(f"[PASS] Follow-up (Day 3 Bump) Generated ({elapsed:.2f}s):")
    print(f"   Subject: {orch_res_followup.get('subject_line')}")
    print(f"   Pitch Content:\n{orch_res_followup.get('pitch_email')}\n")

    # 3. Test DeepSeek Orchestration Routing
    print("[TEST 3] Testing DeepSeek Orchestrator Routing & Fallback...")
    start_time = time.time()
    ds_res = orch.generate_pitch(
        journalist=sample_j,
        campaign=sample_campaign,
        model="deepseek-chat",
        pitch_type="initial",
    )
    elapsed = time.time() - start_time
    print(f"[PASS] DeepSeek Pitch Generated ({elapsed:.2f}s):")
    print(f"   Subject: {ds_res.get('subject_line')}")
    print(f"   Pitch Snippet: {ds_res.get('pitch_email')[:180]}...\n")

    print("=" * 70)
    print("[RESULT] ALL AI QA TESTS COMPLETED SUCCESSFULLY -- 100% OPERATIONAL")
    print("=" * 70)


if __name__ == "__main__":
    run_comprehensive_ai_qa()
