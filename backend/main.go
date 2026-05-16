package main

import (
	"context"
	"log"
	"log/slog"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"anvil/backend/api"
	"anvil/backend/db"
	"anvil/backend/services/pipeline"
	"anvil/backend/services/webhook"
	"anvil/backend/services/websocket"

	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/redis/go-redis/v9"
)

func main() {
	port := getenv("PORT", "8080")
	databaseURL := getenv("DATABASE_URL", "postgres://devsecops:devsecops@localhost:5432/devsecops")
	redisURL := getenv("REDIS_URL", "redis://localhost:6379")

	logger := slog.New(slog.NewJSONHandler(os.Stdout, nil))
	slog.SetDefault(logger)

	// Context for graceful shutdown
	ctx, cancel := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer cancel()

	// 3. Connect to PostgreSQL
	pool, err := pgxpool.New(ctx, databaseURL)
	if err != nil {
		log.Fatalf("failed to connect to postgres: %v", err)
	}
	defer pool.Close()

	if err := pool.Ping(ctx); err != nil {
		log.Fatalf("failed to ping postgres: %v", err)
	}

	// 4. Connect to Redis
	redisOpt, err := redis.ParseURL(redisURL)
	if err != nil {
		log.Fatalf("failed to parse redis URL: %v", err)
	}
	redisClient := redis.NewClient(redisOpt)
	if err := redisClient.Ping(ctx).Err(); err != nil {
		log.Fatalf("failed to connect to redis: %v", err)
	}
	defer redisClient.Close()

	wsHub := websocket.NewHub(logger)

	dbClient := db.NewClient(pool)
	pipelineManager := pipeline.NewManager(dbClient, redisClient, wsHub, logger)

	webhookH := webhook.NewHandler(dbClient, redisClient, logger)
	wsHandler := websocket.NewHandler(wsHub, logger)

	go wsHub.Run()
	go pipelineManager.StartGlobalWSForwarder(ctx)

	router := api.NewRouter(api.Dependencies{
		WebhookHandler:  webhookH,
		PipelineManager: pipelineManager,
		WSHandler:       wsHandler,
		ProjectDB:       dbClient,
		Log:             logger,
	})

	server := &http.Server{
		Addr:    ":" + port,
		Handler: router,
	}

	logger.Info("server starting", "port", port)

	// Start server in background
	go func() {
		if err := server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			logger.Error("server error", "error", err)
		}
	}()

	// Wait for shutdown signal
	<-ctx.Done()
	logger.Info("shutting down server gracefully...")

	shutdownCtx, shutdownCancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer shutdownCancel()

	if err := server.Shutdown(shutdownCtx); err != nil {
		logger.Error("server shutdown error", "error", err)
	}

	logger.Info("server stopped cleanly")
}

func getenv(key, fallback string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return fallback
}
