import 'dart:convert';
import 'package:http/http.dart' as http;
import '../models/scrobbler_state.dart';

class ApiException implements Exception {
  const ApiException(this.message, {this.statusCode});
  final String message;
  final int? statusCode;
  @override
  String toString() => message;
}

class ScrobblerApi {
  ScrobblerApi({
    required this.baseUrl,
    required this.token,
    http.Client? client,
  }) : _client = client ?? http.Client();
  final Uri baseUrl;
  final String token;
  final http.Client _client;

  Future<ScrobblerState> fetchState() async =>
      ScrobblerState.fromJson(await request('GET', '/state/'));

  Future<Map<String, dynamic>> request(
    String method,
    String path, [
    Map<String, dynamic>? body,
    Duration timeout = const Duration(seconds: 8),
  ]) async {
    final request = http.Request(method, baseUrl.resolve(path));
    request.headers.addAll({
      'Authorization': 'Bearer $token',
      'Content-Type': 'application/json',
    });
    if (body != null) request.body = jsonEncode(body);
    final response = await _client
        .send(request)
        .then(http.Response.fromStream)
        .timeout(timeout);
    if (response.statusCode < 200 || response.statusCode >= 300) {
      String? detail;
      try {
        final body = jsonDecode(response.body);
        if (body is Map && body['detail'] is String) {
          detail = body['detail'] as String;
        }
      } on FormatException {
        // Proxies can return HTML errors; use the status fallback below.
      }
      throw ApiException(
        response.statusCode == 401 || response.statusCode == 403
            ? 'Backend authentication failed. Check the API token.'
            : detail ?? 'Backend request failed (${response.statusCode}).',
        statusCode: response.statusCode,
      );
    }
    final result = jsonDecode(response.body);
    if (result is! Map<String, dynamic>) {
      throw const ApiException('Unexpected backend response.');
    }
    return result;
  }

  void close() => _client.close();
}
