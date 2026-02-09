# Food Context Protocol (FCP) API

The Food Context Protocol is an AI-powered food intelligence API that provides comprehensive
meal tracking, analysis, and discovery capabilities.

## ⚠️ Important Disclaimer

**FOR INFORMATIONAL PURPOSES ONLY** - This API provides AI-generated food information and is not intended to provide medical, nutritional, or health advice. Do not rely solely on AI-generated information for:

- **Allergen detection** - AI may miss hidden allergens; always verify with labels and ask directly
- **Food safety** - Check official sources (FDA.gov, USDA.gov) for current recall information
- **Drug-food interactions** - Consult your healthcare provider before making dietary changes while on medications
- **Nutrition data** - Estimates may be inaccurate; use official nutrition labels when available

See the complete legal disclaimers at: https://github.com/Food-Context-Protocol/fcp-gemini-server/blob/main/LEGAL.md

## Features

- **Meal Analysis**: Upload food photos for instant AI-powered nutritional analysis
- **Food Logging**: Track meals with automatic enrichment and categorization
- **Pantry Management**: Monitor ingredients, track expiration, and reduce waste
- **Recipe Generation**: Get personalized recipe suggestions based on your pantry and preferences
- **Food Safety**: Real-time food recall alerts and allergen tracking
- **Discovery**: Find nearby restaurants and dishes matching your taste profile

## Authentication

All endpoints require authentication via Firebase ID token in the `Authorization` header:

```
Authorization: Bearer <firebase-id-token>
```

**Demo Mode**: Requests without authentication receive read-only access to sample data.

## Rate Limits

- Analysis endpoints: 10 requests/minute
- CRUD endpoints: 30 requests/minute
- Search endpoints: 20 requests/minute

## SDKs

Official SDKs are available for:
- Python: `pip install fcp-api`
- TypeScript: `npm install @fcp/client`

## Support

- Documentation: https://docs.fcp.dev
- Issues: https://github.com/Food-Context-Protocol/fcp-gemini-server/issues
