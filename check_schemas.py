#!/usr/bin/env python3
"""
Check which tools have output schemas defined
"""
import requests
import json

def check_tool_schemas():
    """Check which tools have output schemas"""
    try:
        response = requests.get("http://localhost:8000/tools")
        data = response.json()
        
        print("📋 Tool Schema Status")
        print("=" * 50)
        
        tools_with_output = 0
        tools_without_output = 0
        
        for tool in data['tools']:
            name = tool['name']
            has_input = tool['inputSchema'] is not None
            has_output = tool['outputSchema'] is not None
            
            status = "✅" if has_output else "❌"
            print(f"{status} {name:<25} | Input: {'✅' if has_input else '❌'} | Output: {'✅' if has_output else '❌'}")
            
            if has_output:
                tools_with_output += 1
            else:
                tools_without_output += 1
        
        print("\n" + "=" * 50)
        print(f"📊 Summary:")
        print(f"   Tools with output schemas: {tools_with_output}")
        print(f"   Tools without output schemas: {tools_without_output}")
        print(f"   Total tools: {len(data['tools'])}")
        
        if tools_without_output > 0:
            print(f"\n⚠️  {tools_without_output} tools still need output schemas")
        else:
            print(f"\n🎉 All tools have output schemas!")
            
    except Exception as e:
        print(f"❌ Error checking schemas: {e}")

if __name__ == "__main__":
    check_tool_schemas()
