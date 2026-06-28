import asyncio
import sys
sys.path.insert(0, ".")

from app.core.supabase import supabase_client

async def main():
    # Fetch the latest historical metrics
    res = supabase_client.table("historical_metrics").select("*").order("created_at", desc=True).limit(1).execute()
    if not res.data:
        print("No metrics found")
        return
    
    metric = res.data[0]
    print(f"Run ID: {metric.get('run_id')}")
    print(f"Grounding Score: {metric.get('grounding_score')}%")
    print(f"Consistency Score: {metric.get('consistency_score')}%")
    
    # Also get the validation checks if any
    run_id = metric.get('run_id')
    run_res = supabase_client.table("analysis_runs").select("*").eq("id", run_id).execute()
    if run_res.data:
        run = run_res.data[0]
        print(f"Status: {run.get('status')}")
        print(f"Error Message: {run.get('error_message')}")
        
if __name__ == "__main__":
    asyncio.run(main())
