-- CreateSchema
CREATE SCHEMA IF NOT EXISTS "public";

-- CreateEnum
CREATE TYPE "SegmentType" AS ENUM ('narration', 'dialogue', 'thought');

-- CreateEnum
CREATE TYPE "JobStatus" AS ENUM ('queued', 'processing', 'completed', 'failed');

-- CreateTable
CREATE TABLE "users" (
    "id" UUID NOT NULL,
    "email" TEXT,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "users_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "books" (
    "id" UUID NOT NULL,
    "userId" UUID NOT NULL,
    "title" TEXT NOT NULL,
    "author" TEXT,
    "originLanguage" TEXT,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "books_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "chapters" (
    "id" UUID NOT NULL,
    "bookId" UUID NOT NULL,
    "chapterIdx" INTEGER NOT NULL,
    "title" TEXT,
    "rawText" TEXT NOT NULL,
    "status" TEXT NOT NULL DEFAULT 'uploaded',
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "chapters_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "segments" (
    "id" UUID NOT NULL,
    "chapterId" UUID NOT NULL,
    "segmentIdx" INTEGER NOT NULL,
    "text" TEXT NOT NULL,
    "type" "SegmentType" NOT NULL DEFAULT 'narration',
    "characterId" UUID,
    "confidence" DOUBLE PRECISION,
    "audioUrl" TEXT,
    "contentHash" TEXT,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "segments_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "characters" (
    "id" UUID NOT NULL,
    "bookId" UUID NOT NULL,
    "name" TEXT NOT NULL,
    "role" TEXT,
    "voiceId" UUID,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "characters_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "character_profiles" (
    "id" UUID NOT NULL,
    "characterId" UUID NOT NULL,
    "age" TEXT,
    "gender" TEXT,
    "personality" JSONB NOT NULL,
    "speechStyle" JSONB NOT NULL,
    "role" TEXT,
    "voiceNotes" TEXT,
    "confidence" DOUBLE PRECISION,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "character_profiles_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "voice_requirements" (
    "id" UUID NOT NULL,
    "characterId" UUID NOT NULL,
    "pitch" TEXT,
    "ageGroup" TEXT,
    "tone" TEXT,
    "pacing" TEXT,
    "energy" TEXT,
    "avoid" JSONB NOT NULL,
    "rationale" TEXT,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "voice_requirements_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "voices" (
    "id" UUID NOT NULL,
    "provider" TEXT NOT NULL,
    "providerId" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "gender" TEXT,
    "locale" TEXT,
    "pitch" TEXT,
    "ageGroup" TEXT,
    "tone" TEXT,
    "energy" TEXT,
    "sampleUrl" TEXT,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "voices_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "audio_jobs" (
    "id" UUID NOT NULL,
    "chapterId" UUID NOT NULL,
    "status" "JobStatus" NOT NULL DEFAULT 'queued',
    "provider" TEXT,
    "progress" INTEGER NOT NULL DEFAULT 0,
    "error" TEXT,
    "outputUrl" TEXT,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "audio_jobs_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "pronunciation_entries" (
    "id" UUID NOT NULL,
    "bookId" UUID NOT NULL,
    "term" TEXT NOT NULL,
    "phoneme" TEXT NOT NULL,
    "languageCode" TEXT,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "pronunciation_entries_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE UNIQUE INDEX "users_email_key" ON "users"("email");

-- CreateIndex
CREATE INDEX "books_userId_idx" ON "books"("userId");

-- CreateIndex
CREATE INDEX "chapters_bookId_chapterIdx_idx" ON "chapters"("bookId", "chapterIdx");

-- CreateIndex
CREATE UNIQUE INDEX "chapters_bookId_chapterIdx_key" ON "chapters"("bookId", "chapterIdx");

-- CreateIndex
CREATE INDEX "segments_chapterId_segmentIdx_idx" ON "segments"("chapterId", "segmentIdx");

-- CreateIndex
CREATE UNIQUE INDEX "segments_chapterId_segmentIdx_key" ON "segments"("chapterId", "segmentIdx");

-- CreateIndex
CREATE INDEX "characters_bookId_name_idx" ON "characters"("bookId", "name");

-- CreateIndex
CREATE UNIQUE INDEX "character_profiles_characterId_key" ON "character_profiles"("characterId");

-- CreateIndex
CREATE UNIQUE INDEX "voice_requirements_characterId_key" ON "voice_requirements"("characterId");

-- CreateIndex
CREATE UNIQUE INDEX "voices_provider_providerId_key" ON "voices"("provider", "providerId");

-- CreateIndex
CREATE INDEX "audio_jobs_chapterId_status_idx" ON "audio_jobs"("chapterId", "status");

-- CreateIndex
CREATE UNIQUE INDEX "pronunciation_entries_bookId_term_key" ON "pronunciation_entries"("bookId", "term");

-- AddForeignKey
ALTER TABLE "books" ADD CONSTRAINT "books_userId_fkey" FOREIGN KEY ("userId") REFERENCES "users"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "chapters" ADD CONSTRAINT "chapters_bookId_fkey" FOREIGN KEY ("bookId") REFERENCES "books"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "segments" ADD CONSTRAINT "segments_chapterId_fkey" FOREIGN KEY ("chapterId") REFERENCES "chapters"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "segments" ADD CONSTRAINT "segments_characterId_fkey" FOREIGN KEY ("characterId") REFERENCES "characters"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "characters" ADD CONSTRAINT "characters_bookId_fkey" FOREIGN KEY ("bookId") REFERENCES "books"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "character_profiles" ADD CONSTRAINT "character_profiles_characterId_fkey" FOREIGN KEY ("characterId") REFERENCES "characters"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "voice_requirements" ADD CONSTRAINT "voice_requirements_characterId_fkey" FOREIGN KEY ("characterId") REFERENCES "characters"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "audio_jobs" ADD CONSTRAINT "audio_jobs_chapterId_fkey" FOREIGN KEY ("chapterId") REFERENCES "chapters"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "pronunciation_entries" ADD CONSTRAINT "pronunciation_entries_bookId_fkey" FOREIGN KEY ("bookId") REFERENCES "books"("id") ON DELETE CASCADE ON UPDATE CASCADE;

