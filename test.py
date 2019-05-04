import json

import graphene
from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop
from graphql_ws.aiohttp import AiohttpSubscriptionServer


class SyncData(graphene.ObjectType):
    field = graphene.Field(graphene.Boolean)

    def resolve_field(self, _):
        return True


class AsyncData(graphene.ObjectType):
    field = graphene.Field(graphene.Boolean)

    async def resolve_field(self, _):
        return True


class Subscription(graphene.ObjectType):
    sync_data = graphene.Field(SyncData)
    async_data = graphene.Field(AsyncData)

    async def resolve_sync_data(self, _):
        yield SyncData()

    async def resolve_async_data(self, _):
        yield AsyncData()


class MyAppTestCase(AioHTTPTestCase):
    async def get_application(self):
        async def subscriptions(request):
            subscription_server = AiohttpSubscriptionServer(
                graphene.Schema(subscription=Subscription)
            )
            ws = web.WebSocketResponse(protocols=('graphql-ws',))
            await ws.prepare(request)

            await subscription_server.handle(ws)
            return ws

        app = web.Application()
        app.router.add_get('/subscriptions', subscriptions)
        return app

    async def setUpAsync(self) -> None:
        self.ws_client = await self.client.ws_connect(
            '/subscriptions', timeout=1
        )

    @unittest_run_loop
    async def test_sync(self):
        await self.ws_client.send_str(json.dumps({
            "id": 1,
            "type": "start",
            "payload": {
                'query': "subscription{ syncData { field } }",
                'variables': None
            }
        }))
        data = await self.ws_client.receive_str(timeout=1)
        self.assertEqual(
            json.loads(data),
            {
                "id": 1,
                "type": "data",
                "payload": {"data": {"syncData": {"field": True}}}
            }
        )  # Ok

    @unittest_run_loop
    async def test_async(self):
        await self.ws_client.send_str(json.dumps({
            "id": 1,
            "type": "start",
            "payload": {
                'query': "subscription{ asyncData { field } }",
                'variables': None
            }
        }))
        data = await self.ws_client.receive_str(timeout=1)
        self.assertEqual(
            json.loads(data),
            {
                "id": 1,
                "type": "data",
                "payload": {"data": {"asyncData": {"field": True}}}
            }
        )  # Assertion failed
