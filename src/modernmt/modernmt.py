import base64
import json
import time

import jwt
import requests


class ModernMTException(Exception):
    def __init__(self, status, type, message, metadata=None) -> None:
        super().__init__("(%s) %s" % (type, message))

        self.status = status
        self.type = type
        self.message = message

        if metadata is not None:
            self.metadata = metadata


class ModernMT(object):
    def __init__(self, api_key, platform="modernmt-python", platform_version="1.2.0", api_client=None) -> None:
        self.__batch_public_key = None
        self.__batch_public_key_timestamp = 0

        self.__base_url = "https://api.modernmt.com"
        self.__headers = {
            "MMT-ApiKey": api_key,
            "MMT-Platform": platform,
            "MMT-PlatformVersion": platform_version
        }

        if api_client is not None:
            self.__headers["MMT-ApiClient"] = str(api_client)

        self.memories = _MemoryServices(self.__headers, self.__send)

    def list_supported_languages(self):
        return self.__send("get", "/translate/languages")

    def detect_language(self, q, format=None):
        data = {"q": q}
        if format is not None:
            data["format"] = format

        res = self.__send("get", "/translate/detect", data=data)

        if not isinstance(q, list):
            return DetectedLanguage(res)

        languages = []
        for el in res:
            languages.append(DetectedLanguage(el))

        return languages

    def translate(self, source, target, q, hints=None, context_vector=None, options=None):
        data = {"target": target, "q": q}
        if source is not None:
            data["source"] = source
        if context_vector is not None:
            data["context_vector"] = context_vector
        if hints is not None:
            if isinstance(hints, list):
                hints = ",".join(map(str, hints))
            data["hints"] = hints

        if options is not None:
            if "priority" in options:
                data["priority"] = options["priority"]
            if "project_id" in options:
                data["project_id"] = options["project_id"]
            if "multiline" in options:
                data["multiline"] = options["multiline"]
            if "timeout" in options:
                data["timeout"] = options["timeout"]
            if "format" in options:
                data["format"] = options["format"]
            if "alt_translations" in options:
                data["alt_translations"] = options["alt_translations"]

        res = self.__send("get", "/translate", data=data)

        if not isinstance(q, list):
            return Translation(res)

        translations = []
        for el in res:
            translations.append(Translation(el))

        return translations

    def batch_translate(self, webhook, source, target, q, hints=None, context_vector=None, options=None):
        data = {
            "webhook": webhook,
            "target": target,
            "q": q
        }

        if context_vector is not None:
            data["context_vector"] = context_vector
        if hints is not None:
            if isinstance(hints, list):
                hints = ",".join(map(str, hints))
            data["hints"] = hints

        if source is not None:
            data["source"] = source

        if options is not None:
            if "project_id" in options:
                data["project_id"] = options["project_id"]
            if "multiline" in options:
                data["multiline"] = options["multiline"]
            if "format" in options:
                data["format"] = options["format"]
            if "alt_translations" in options:
                data["alt_translations"] = options["alt_translations"]
            if "metadata" in options:
                data["metadata"] = options["metadata"]

        headers = None
        if options is not None and "idempotency_key" in options:
            headers = { "x-idempotency-key": options["idempotency_key"] }

        res = self.__send("post", "/translate/batch", data=data, headers=headers)

        return res["enqueued"]

    def handle_callback(self, data, signature):
        if self.__batch_public_key is None:
            self.__refresh_public_key()

        if time.time() - self.__batch_public_key_timestamp > 3600:
            # noinspection PyBroadException
            try:
                self.__refresh_public_key()
            except:
                pass

        jwt.decode(signature, self.__batch_public_key, algorithms=["RS256"])

        if isinstance(data, str):
            data = json.loads(data)

        result = data["result"]
        metadata = data.get("metadata", None)
        error = result.get("error", None)

        if error is not None:
            raise ModernMTException(result["status"], error["type"], error["message"], metadata)

        return BatchTranslation(data)

    def __refresh_public_key(self):
        data = self.__send("get", "/translate/batch/key")
        self.__batch_public_key = base64.b64decode(data["publicKey"])
        self.__batch_public_key_timestamp = time.time()

    def get_context_vector(self, source, targets, text, hints=None, limit=None):
        data = {"source": source, "text": text, "targets": targets}

        if hints is not None:
            if isinstance(hints, list):
                hints = ",".join(map(str, hints))
            data["hints"] = hints
        if limit is not None:
            data["limit"] = limit

        res = self.__send("get", "/context-vector", data=data)

        if isinstance(targets, list):
            return res["vectors"]
        else:
            if targets in res["vectors"]:
                return res["vectors"][targets]
            else:
                return None

    def get_context_vector_from_file(self, source, targets, file, hints=None, limit=None, compression=None):
        if isinstance(file, str):
            file = open(file, "rb")

        data = {"source": source, "targets": targets}

        if hints is not None:
            if isinstance(hints, list):
                hints = ",".join(map(str, hints))
            data["hints"] = hints
        if limit is not None:
            data["limit"] = limit
        if compression is not None:
            data["compression"] = compression

        res = self.__send("get", "/context-vector", data=data, files={"content": file})

        if isinstance(targets, list):
            return res["vectors"]
        else:
            if targets in res["vectors"]:
                return res["vectors"][targets]
            else:
                return None

    def __send(self, method, endpoint, data=None, files=None, cls=None, headers=None):
        url = self.__base_url + endpoint

        _headers = self.__headers
        _headers["X-HTTP-Method-Override"] = method

        if headers is not None:
            _headers.update(headers)

        if files is None:
            r = requests.post(url, headers=_headers, json=data)
        else:
            r = requests.post(url, headers=_headers, data=data, files=files)

        _json = r.json()
        if r.status_code != requests.codes.ok:
            ex_type = "UnknownException"
            ex_msg = r.text
            try:
                error = _json["error"]
                ex_type, ex_msg = error["type"], error["message"]
            except KeyError:
                pass
            except ValueError:
                pass

            raise ModernMTException(r.status_code, ex_type, ex_msg)

        return _json["data"] if cls is None else cls(_json["data"])


class _MemoryServices(object):
    def __init__(self, headers, send) -> None:
        self.__headers = headers
        self.__send = send

    def list(self):
        res = self.__send("get", "/memories")

        memories = []
        for el in res:
            memories.append(Memory(el))

        return memories

    def get(self, id):
        return self.__send("get", "/memories/%s" % id, cls=Memory)

    def create(self, name, description=None, external_id=None):
        data = {"name": name}
        if description is not None:
            data["description"] = description
        if external_id is not None:
            data["external_id"] = external_id

        return self.__send("post", "/memories", data=data, cls=Memory)

    def edit(self, id, name=None, description=None):
        data = {}
        if name is not None:
            data["name"] = name
        if description is not None:
            data["description"] = description

        return self.__send("put", "/memories/%s" % id, data=data, cls=Memory)

    def delete(self, id):
        return self.__send("delete", "/memories/%s" % id, cls=Memory)

    def add(self, id, source, target, sentence, translation, tuid=None):
        data = {"source": source, "target": target, "sentence": sentence, "translation": translation}
        if tuid is not None:
            data["tuid"] = tuid

        return self.__send("post", "/memories/%s/content" % id, data=data, cls=ImportJob)

    def replace(self, id, tuid, source, target, sentence, translation):
        data = {"tuid": tuid, "source": source, "target": target, "sentence": sentence, "translation": translation}
        return self.__send("put", "/memories/%s/content" % id, data=data, cls=ImportJob)

    def import_tmx(self, id, tmx, compression=None):
        if isinstance(tmx, str):
            tmx = open(tmx, "rb")

        data = {}
        if compression is not None:
            data["compression"] = compression

        return self.__send("post", "/memories/%s/content" % id, data=data, files={"tmx": tmx}, cls=ImportJob)

    def get_import_status(self, uuid):
        return self.__send("get", "/import-jobs/%s" % uuid, cls=ImportJob)


class _Model(object):
    def __init__(self, data, fields) -> None:
        self.__dict__ = {k: v for k, v in data.items() if k in fields}

    def __repr__(self):
        return str(self)

    def __str__(self):
        return str(vars(self))


class Translation(_Model):
    def __init__(self, data) -> None:
        super().__init__(data, [
            "translation",
            "contextVector",
            "characters",
            "billedCharacters",
            "detectedLanguage",
            "altTranslations"
        ])


class BatchTranslation(_Model):
    def __init__(self, data) -> None:
        super().__init__({}, [])

        _data = data["result"]["data"]

        if not isinstance(_data, list):
            self.__dict__["data"] = Translation(_data)
        else:
            self.__dict__["data"] = []
            for el in _data:
                self.__dict__["data"].append(Translation(el))

        if "metadata" in data:
            self.__dict__["metadata"] = data["metadata"]


class Memory(_Model):
    def __init__(self, data) -> None:
        super().__init__(data, ["id", "name", "description", "creationDate"])


class ImportJob(_Model):
    def __init__(self, data) -> None:
        super().__init__(data, ["id", "memory", "size", "progress"])


class DetectedLanguage(_Model):
    def __init__(self, data) -> None:
        super().__init__(data, ["billedCharacters", "detectedLanguage"])
