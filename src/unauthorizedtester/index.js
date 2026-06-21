// Copyright 2024 - Microservicio de prueba Zero Trust
//
// Este microservicio intenta llamar a paymentservice sin autorización.
// Demuestra que las AuthorizationPolicies de Istio bloquean el acceso.

const path = require('path');
const grpc = require('@grpc/grpc-js');
const protoLoader = require('@grpc/proto-loader');
const http = require('http');

const PORT = process.env.PORT || 8080;
const PAYMENT_SERVICE_ADDR = process.env.PAYMENT_SERVICE_ADDR || 'paymentservice:50051';

// Cargar el proto de paymentservice
const PROTO_PATH = path.join(__dirname, 'proto', 'demo.proto');

let paymentClient = null;

function loadProto() {
  try {
    const packageDefinition = protoLoader.loadSync(PROTO_PATH, {
      keepCase: true,
      longs: String,
      enums: String,
      defaults: true,
      oneofs: true
    });
    const hipsterShop = grpc.loadPackageDefinition(packageDefinition).hipstershop;
    paymentClient = new hipsterShop.PaymentService(
      PAYMENT_SERVICE_ADDR,
      grpc.credentials.createInsecure()
    );
    console.log(`[INFO] Cliente gRPC configurado para ${PAYMENT_SERVICE_ADDR}`);
  } catch (err) {
    console.error('[ERROR] No se pudo cargar el proto:', err.message);
  }
}

// Intentar llamar a paymentservice
function tryCallPaymentService() {
  return new Promise((resolve, reject) => {
    if (!paymentClient) {
      reject(new Error('Cliente gRPC no inicializado'));
      return;
    }

    console.log('[INFO] Intentando llamar a PaymentService.Charge...');
    console.log('[INFO] Este llamado DEBERÍA SER DENEGADO por Istio (Zero Trust)');

    const chargeRequest = {
      amount: {
        currency_code: 'USD',
        units: 10,
        nanos: 0
      },
      credit_card: {
        credit_card_number: '4242424242424242',
        credit_card_cvv: 123,
        credit_card_expiration_year: 2030,
        credit_card_expiration_month: 12
      }
    };

    const deadline = new Date();
    deadline.setSeconds(deadline.getSeconds() + 5);

    paymentClient.Charge(chargeRequest, { deadline }, (err, response) => {
      if (err) {
        console.error('[ERROR] Llamada a PaymentService DENEGADA:', err.message);
        console.error('[ERROR] Código de error:', err.code);
        console.error('[INFO] ¡Esto es lo esperado! Zero Trust está funcionando.');
        reject(err);
      } else {
        console.log('[WARN] Llamada exitosa (no debería pasar con Zero Trust):', response);
        resolve(response);
      }
    });
  });
}

// Servidor HTTP simple para probar
const server = http.createServer(async (req, res) => {
  console.log(`[INFO] Request recibido: ${req.method} ${req.url}`);

  if (req.url === '/test-payment') {
    try {
      const result = await tryCallPaymentService();
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({
        status: 'success',
        message: 'Llamada exitosa (Zero Trust NO está funcionando correctamente)',
        data: result
      }));
    } catch (err) {
      res.writeHead(403, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({
        status: 'blocked',
        message: 'Acceso DENEGADO por Istio - Zero Trust funcionando correctamente',
        error: err.message,
        errorCode: err.code
      }));
    }
  } else if (req.url === '/health') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ status: 'healthy' }));
  } else {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({
      service: 'unauthorized-tester',
      description: 'Microservicio de prueba para demostrar Zero Trust',
      endpoints: {
        '/test-payment': 'Intenta llamar a paymentservice (será denegado)',
        '/health': 'Health check'
      }
    }));
  }
});

// Inicializar
loadProto();

server.listen(PORT, () => {
  console.log('================================================');
  console.log('  UNAUTHORIZED TESTER - Zero Trust Demo');
  console.log('================================================');
  console.log(`[INFO] Servidor escuchando en puerto ${PORT}`);
  console.log(`[INFO] PaymentService target: ${PAYMENT_SERVICE_ADDR}`);
  console.log('[INFO] Este servicio NO tiene permiso para llamar a PaymentService');
  console.log('[INFO] Usa /test-payment para probar el bloqueo de Istio');
  console.log('================================================');
});
