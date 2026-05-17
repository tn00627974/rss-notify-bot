-- Rss 來源 
CREATE TABLE rss_source (
    id BIGSERIAL PRIMARY KEY,
    rss_url VARCHAR(500) NOT NULL, -- Rss網址
    display_name VARCHAR(50) NOT NULL, -- 傳送訊息的標頭名稱 : 平民百姓
    is_active BOOLEAN NOT NULL DEFAULT TRUE, -- 是否啟用 或 停用 
    description VARCHAR(100),
    create_time TIMESTAMP NOT NULL DEFAULT NOW()
);
-- 推送平台
CREATE TABLE platform (
    id BIGSERIAL PRIMARY KEY,
	name VARCHAR(20) NOT NULL, -- discord , line ..
    create_time TIMESTAMP NOT NULL DEFAULT NOW()
);
-- 推播
CREATE TABLE target (
    id BIGSERIAL PRIMARY KEY,
	platform_id BIGINT NOT NULL,
	external_id VARCHAR(100) NOT NULL, -- Dc channel , line groupId
	mention_user_id VARCHAR(100), -- Dc userId
	description VARCHAR(100) ,
    create_time TIMESTAMP NOT NULL DEFAULT NOW()
);
-- 多對多關聯 ( Rss 與 Target)
CREATE TABLE rss_source_target(
    id BIGSERIAL PRIMARY KEY,
	rss_source_id BIGINT NOT NULL,
	target_id BIGINT NOT NULL,
    create_time TIMESTAMP NOT NULL DEFAULT NOW()
);

ALTER TABLE target
ADD CONSTRAINT fk_target_platform
FOREIGN KEY (platform_id) REFERENCES platform(id);
 
ALTER TABLE target
ADD CONSTRAINT ux_target_platform_external  
UNIQUE (platform_id, external_id); -- 防止重複

ALTER TABLE rss_source_target
ADD CONSTRAINT fk_rst_rss  
FOREIGN KEY (rss_source_id) REFERENCES rss_source(id);

ALTER TABLE rss_source_target
ADD CONSTRAINT fk_rst_target  
FOREIGN KEY (target_id) REFERENCES target(id);
  
ALTER TABLE rss_source_target
ADD CONSTRAINT ux_rst_unique  
UNIQUE (rss_source_id, target_id); -- 防止重複