"""
Auth 路由 API 单元测试
"""
import pytest

from app.core.security import create_token_pair


class TestAuthRouter:
    """Auth 路由接口单元测试类"""

    def test_get_rsa_key(self, client):
        """测试获取 RSA 公钥"""
        response = client.get("/api/v1/auth/rsa-key")
        assert response.status_code == 200
        json_data = response.json()
        assert json_data["code"] == 0
        assert "BEGIN PUBLIC KEY" in json_data["data"]["public_key"]

    def test_login_returns_token_pair(self, client):
        """测试登录接口返回双 Token 对"""
        payload = {"username": "admin", "password": "password123"}
        response = client.post("/api/v1/auth/login", json=payload)
        assert response.status_code == 200
        json_data = response.json()
        assert json_data["code"] == 0
        data = json_data["data"]
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["expires_in"] == 1800
        assert data["refresh_expires_in"] == 7 * 86400

    def test_refresh_token_rotation(self, client, redis_mock):
        """测试 Refresh Token 刷新轮换"""
        login_res = client.post("/api/v1/auth/login", json={"username": "admin", "password": "pass"})
        refresh_token = login_res.json()["data"]["refresh_token"]

        response = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["access_token"]
        assert data["refresh_token"]
        assert data["refresh_token"] != refresh_token

    def test_refresh_token_replay_attack_revokes_session(self, client, redis_mock):
        """测试 Refresh Token 重放攻击被阻止并触发撤销"""
        login_res = client.post("/api/v1/auth/login", json={"username": "admin", "password": "pass"})
        refresh_token = login_res.json()["data"]["refresh_token"]

        # 第一次刷新成功
        res1 = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
        assert res1.status_code == 200

        # 第二次使用旧的 refresh_token（重放攻击）
        res2 = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
        assert res2.status_code == 401
        assert res2.json()["data"]["reason"] == "refresh_token_reused"

    def test_logout(self, client, redis_mock):
        """测试登出接口"""
        login_res = client.post("/api/v1/auth/login", json={"username": "admin", "password": "pass"})
        access_token = login_res.json()["data"]["access_token"]
        refresh_token = login_res.json()["data"]["refresh_token"]

        headers = {"Authorization": f"Bearer {access_token}"}
        logout_res = client.post("/api/v1/auth/logout", headers=headers, json={"refresh_token": refresh_token})
        assert logout_res.status_code == 200
        assert logout_res.json()["data"]["success"] is True

        # 登出后再用 access_token 访问 /me 应该失败 (Token 已加入黑名单)
        me_res = client.get("/api/v1/auth/me", headers=headers)
        assert me_res.status_code == 401

    def test_get_me_authenticated(self, client, redis_mock):
        """测试使用有效 Token 获取当前用户信息"""
        login_res = client.post("/api/v1/auth/login", json={"username": "admin", "password": "pass"})
        access_token = login_res.json()["data"]["access_token"]

        headers = {"Authorization": f"Bearer {access_token}"}
        response = client.get("/api/v1/auth/me", headers=headers)
        assert response.status_code == 200
        assert response.json()["data"]["id"] == 1
