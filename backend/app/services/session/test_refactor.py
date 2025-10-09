"""
Quick test to verify the refactored session modules work correctly.
Run with: python -m backend.app.services.session.test_refactor
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

def test_imports():
    """Test that all imports work correctly."""
    print("Testing imports...")
    
    try:
        from services.session.storage import get_storage
        print("✅ storage.py imports OK")
        
        from services.session.anonymization import store_anonymization_map, get_anonymization_map
        print("✅ anonymization.py imports OK")
        
        from services.session.llm_data import (
            store_llm_response, 
            get_llm_response,
            store_anonymized_request,
            get_anonymized_request
        )
        print("✅ llm_data.py imports OK")
        
        from services.session.manager import (
            SessionManager,
            get_session_manager,
            get_session_status,
            delete_session
        )
        print("✅ manager.py imports OK")
        
        from services.session import (
            store_anonymization_map,
            get_anonymization_map,
            get_session_status,
            delete_session,
            store_llm_response,
            get_llm_response
        )
        print("✅ __init__.py imports OK")
        
        print("\n✅ All imports successful!")
        return True
        
    except Exception as e:
        print(f"\n❌ Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_basic_functionality():
    """Test basic storage and retrieval."""
    print("\nTesting basic functionality...")
    
    try:
        from services.session import (
            store_anonymization_map,
            get_anonymization_map,
            store_llm_response,
            get_llm_response,
            delete_session
        )
        
        test_session = "test_refactor_001"
        test_map = {
            "Juan Pérez": "María González",
            "juan@email.com": "maria@email.com"
        }
        test_llm_response = "Hola María González, tu email es maria@email.com"
        
        print(f"Storing test data for session: {test_session}")
        store_anonymization_map(test_session, test_map)
        print("✅ Map stored")
        
        store_llm_response(test_session, test_llm_response)
        print("✅ LLM response stored")
        
        retrieved_map = get_anonymization_map(test_session)
        assert retrieved_map == test_map
        print("✅ Map retrieved and matches")
        
        retrieved_response = get_llm_response(test_session)
        assert retrieved_response == test_llm_response
        print("✅ LLM response retrieved and matches")
        
        delete_session(test_session)
        print("✅ Session deleted")
        
        print("\n✅ All functionality tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Functionality test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("REFACTORED SESSION MODULE TEST")
    print("=" * 60)
    
    imports_ok = test_imports()
    
    if imports_ok:
        functionality_ok = test_basic_functionality()
        
        if functionality_ok:
            print("\n" + "=" * 60)
            print("✅ ALL TESTS PASSED - Refactoring successful!")
            print("=" * 60)
            sys.exit(0)
    
    print("\n" + "=" * 60)
    print("❌ TESTS FAILED - Check errors above")
    print("=" * 60)
    sys.exit(1)