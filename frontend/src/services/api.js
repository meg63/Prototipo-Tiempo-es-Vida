const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api').replace(/\/+$/, '');

const TOKEN_KEY = 'tiempo_es_vida_token';
const USER_KEY = 'tiempo_es_vida_user';

export class ApiError extends Error {
  constructor(message, status, data = null) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function getStoredUser() {
  try {
    const value = localStorage.getItem(USER_KEY);
    return value ? JSON.parse(value) : null;
  } catch {
    return null;
  }
}

export function saveAuthSession(payload) {
  if (!payload?.token || !payload?.usuario) {
    throw new Error('El servidor no devolvió un token y un usuario válidos.');
  }
  localStorage.setItem(TOKEN_KEY, payload.token);
  localStorage.setItem(USER_KEY, JSON.stringify(payload.usuario));
  return payload.usuario;
}

export function clearAuthSession() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

export function hasAuthToken() {
  return Boolean(getToken());
}

function explainError(data, fallback) {
  if (!data) return fallback;
  if (typeof data === 'string') return data;
  if (typeof data.detail === 'string') return data.detail;
  if (typeof data.non_field_errors?.[0] === 'string') return data.non_field_errors[0];

  const messages = [];
  for (const [field, value] of Object.entries(data)) {
    const values = Array.isArray(value) ? value : [value];
    for (const item of values) {
      if (typeof item === 'string') messages.push(`${field}: ${item}`);
      else if (item && typeof item === 'object') messages.push(`${field}: ${JSON.stringify(item)}`);
    }
  }
  return messages.length ? messages.join(' · ') : fallback;
}

async function request(path, options = {}) {
  const {
    method = 'GET',
    body,
    auth = true,
    headers: customHeaders = {},
    ...fetchOptions
  } = options;

  const headers = new Headers(customHeaders);
  const token = getToken();
  if (auth && token) headers.set('Authorization', `Token ${token}`);

  let requestBody = body;
  const isFormData = typeof FormData !== 'undefined' && body instanceof FormData;
  if (body !== undefined && body !== null && !isFormData && typeof body !== 'string') {
    headers.set('Content-Type', 'application/json');
    requestBody = JSON.stringify(body);
  }

  let response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...fetchOptions,
      method,
      headers,
      body: requestBody,
    });
  } catch {
    throw new ApiError(
      'No fue posible comunicarse con Django. Compruebe que Docker esté activo y que VITE_API_BASE_URL apunte al backend.',
      0,
    );
  }

  const raw = await response.text();
  let data = null;
  if (raw) {
    try {
      data = JSON.parse(raw);
    } catch {
      data = raw;
    }
  }

  if (!response.ok) {
    if (response.status === 401 && auth) clearAuthSession();
    throw new ApiError(
      explainError(data, `La solicitud falló (${response.status}).`),
      response.status,
      data,
    );
  }

  return data;
}

export const api = {
  auth: {
    async register(payload) {
      const response = await request('/auth/register/', { method: 'POST', body: payload, auth: false });
      saveAuthSession(response);
      return response;
    },
    async login(payload) {
      const response = await request('/auth/login/', { method: 'POST', body: payload, auth: false });
      saveAuthSession(response);
      return response;
    },
    me() {
      return request('/auth/me/');
    },
    async logout() {
      try {
        return await request('/auth/logout/', { method: 'POST' });
      } finally {
        clearAuthSession();
      }
    },
  },
  consent: {
    get() {
      return request('/consentimiento/');
    },
    create(payload) {
      return request('/consentimiento/', { method: 'POST', body: payload });
    },
  },
  profile: {
    get() {
      return request('/perfil/');
    },
    save(payload) {
      return request('/perfil/', { method: 'PUT', body: payload });
    },
    update(payload) {
      return request('/perfil/', { method: 'PATCH', body: payload });
    },
  },
  habits: {
    submitMorning(payload) {
      return request('/habitos/manana/', { method: 'POST', body: payload });
    },
    submitNight(payload) {
      return request('/habitos/noche/', { method: 'POST', body: payload });
    },
    list({ periodo = '7', categoria = '' } = {}) {
      const query = new URLSearchParams({ periodo });
      if (categoria) query.set('categoria', categoria);
      return request(`/habitos/?${query.toString()}`);
    },
  },
  recommendations: {
    list() {
      return request('/recomendaciones/');
    },
    updateClarity(id, respuesta_claridad) {
      return request(`/recomendaciones/${id}/claridad/`, {
        method: 'PATCH',
        body: { respuesta_claridad },
      });
    },
  },
};

export function getApiErrorMessage(error) {
  if (error instanceof ApiError) return error.message;
  return error?.message || 'Ocurrió un error inesperado.';
}
