import pytest

from app.config import settings
from app.moolabel import model
from app.moolabel.labels import LABELS

URL = "/v1/moolabel/predict"
CATATAN_16 = "sausnya pisah yaa, sendoknya jgn lupa"  # KF 9.6 contoh 16


@pytest.fixture(autouse=True)
def cache_bersih():
    yield
    model.load_model.cache_clear()


def kirim(client, auth, *notes, ids=None):
    ids = ids or list(range(1, len(notes) + 1))
    items = [{"order_item_id": i, "note": n} for i, n in zip(ids, notes)]
    return client.post(URL, json={"items": items}, headers=auth)


def test_tanpa_secret_401(client):
    body = {"items": [{"order_item_id": 1, "note": CATATAN_16}]}
    assert client.post(URL, json=body).status_code == 401
    assert client.post(URL, json=body, headers={"X-Internal-Secret": "salah"}).status_code == 401


def test_sesuai_kontrak(client, auth):
    r = kirim(client, auth, CATATAN_16, ids=[16])
    assert r.status_code == 200
    body = r.json()
    assert set(body) == {"model_version", "items"}
    assert body["model_version"] == "linsvm-v2"
    item = body["items"][0]
    assert set(item) == {"order_item_id", "labels", "scores"}
    assert item["order_item_id"] == 16
    assert item["labels"] == ["saus_terpisah", "alat_makan"]
    assert list(item["scores"]) == LABELS


def test_catatan_kosong_422(client, auth):
    assert kirim(client, auth, "").status_code == 422
    assert kirim(client, auth, "   ").status_code == 422


def test_batas_panjang(client, auth):
    assert kirim(client, auth, "a" * 500).status_code == 200
    assert kirim(client, auth, "a" * 501).status_code == 422


def test_batas_jumlah_item(client, auth):
    assert client.post(URL, json={"items": []}, headers=auth).status_code == 422
    assert kirim(client, auth, *["sendok 2"] * 51).status_code == 422
    r = kirim(client, auth, *["sendok 2"] * 50)
    assert r.status_code == 200
    assert len(r.json()["items"]) == 50


def test_urutan_dan_id_ganda(client, auth):
    r = kirim(client, auth, CATATAN_16, "makasih kak, semangat jualannya", "saya alergi kacang",
              ids=[3, 1, 3])
    items = r.json()["items"]
    assert [i["order_item_id"] for i in items] == [3, 1, 3]
    assert items[0]["labels"] == ["saus_terpisah", "alat_makan"]
    assert items[1]["labels"] == []
    assert "alergi" in items[2]["labels"]


def test_catatan_tanpa_huruf(client, auth):
    r = kirim(client, auth, "-", "!!!")
    assert r.status_code == 200
    for item in r.json()["items"]:
        assert item["labels"] == []
        assert list(item["scores"]) == LABELS


def test_model_gagal_503(client, auth, monkeypatch):
    monkeypatch.setattr(settings, "moolabel_model_sha256", "0" * 64)
    model.load_model.cache_clear()
    r = kirim(client, auth, CATATAN_16)
    assert r.status_code == 503
    assert r.json() == {"detail": "MooLabel unavailable"}
