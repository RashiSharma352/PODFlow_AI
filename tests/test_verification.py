from backend.verification import inspect_image
def test_missing_file_never_auto_approves(tmp_path):
    result=inspect_image(str(tmp_path/"missing.jpg"),"LR-1")
    assert result["status"]=="Needs review"
    assert result["confidence"]=="low"
    assert result["flags"]
