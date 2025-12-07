import models, database, os, shutil
from ingest import ingest_media
from process import process_media
from sqlalchemy.orm import Session

db = database.SessionLocal()

def run_test():
    print("=== Re-ID Verification Test ===")
    
    # 1. Reset DB (soft delete)
    db.query(models.OfficerAppearance).delete()
    db.query(models.Officer).delete()
    db.query(models.Media).delete()
    db.commit()
    
    # 2. Ingest Image 1
    print("\n1. Processing First Image...")
    # Ensure test file exists
    src = "../data/media/test_officer_face.png"
    if not os.path.exists(src):
        print("Error: Test image not found.")
        return

    import datetime
    # Manually create media
    media1 = models.Media(url=src, type="image", protest_id=1, timestamp=datetime.datetime.utcnow())
    db.add(media1)
    db.commit()
    db.refresh(media1)
    
    process_media(media1.id)
    
    officers = db.query(models.Officer).all()
    if len(officers) != 1:
        print(f"FAIL: Expected 1 officer, found {len(officers)}")
        return
    
    officer1 = officers[0]
    print(f"Created Officer ID: {officer1.id}")
    
    # 3. Ingest Image 2 (Clone)
    print("\n2. Processing Second Image (Clone)...")
    src2 = "../data/media/test_officer_face_2.png"
    shutil.copy(src, src2)
    
    media2 = models.Media(url=src2, type="image", protest_id=1, timestamp=datetime.datetime.utcnow())
    db.add(media2)
    db.commit()
    db.refresh(media2)
    
    process_media(media2.id)
    
    # 4. Check results
    officers_final = db.query(models.Officer).all()
    print(f"Total Officers: {len(officers_final)}")
    
    # Check appearances for Officer 1
    apps = db.query(models.OfficerAppearance).filter(models.OfficerAppearance.officer_id == officer1.id).all()
    print(f"Officer {officer1.id} has {len(apps)} appearances")
    
    if len(officers_final) == 1 and len(apps) == 2:
        print("\n✅ PASS: Re-ID successfully linked the officer!")
    else:
        print("\n❌ FAIL: Re-ID failed to link.")
        if len(officers_final) > 1:
            print("  -> Creating duplicate officers instead of merging.")

if __name__ == "__main__":
    try:
        run_test()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
