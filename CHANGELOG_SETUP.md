# Setup Version History cho Changelog Script

Khi tạo repository mới, bạn cần thiết lập version history để changelog script có thể hoạt động.

## Bước 1: Tạo Initial Commit

```bash
cd /path/to/ci-data-works-arc
git init
git add .
git commit -m "Initial commit"
```

## Bước 2: Setup Version Tags (Optional)

Chạy script setup tự động:
```bash
bash setup-changelog.sh
```

Hoặc setup manual:

### Cách Manual:

a) **Tạo commit với version change:**
```bash
git commit -am "bump: version 2.4.7.53"
```

b) **Tạo tag cho version đó:**
```bash
git tag -a v2.4.7.53 -m "Release v2.4.7.53"
```

c) **Push lên GitHub:**
```bash
git push origin dev
git push origin dev --tags
```

## Bước 3: Cách Hoạt động

Script `generate_changelog.py` tìm kiếm những lần **Version:** line thay đổi trong `plug.php`.

**Ví dụ quy trình:**

```
Repo mới tạo
  ↓
Initial commit: plug.php Version: 2.4.7.50
  ↓
Merge PR: Updated Version: 2.4.7.51 → Changelog có entry
  ↓
Merge PR: Updated Version: 2.4.7.52 → Changelog có entry
```

## Bước 4: Trigger Changelog Generator

### Cách 1: Tự động (qua GitHub Actions)
```bash
# Tạo PR, merge vào dev, GitHub Actions sẽ auto run
# Nếu plug.php version thay đổi → Changelog được generate
```

### Cách 2: Manual
```bash
# Chạy local
python run_scripts/generate_changelog.py

# Commit changes
git add log.txt
git commit -m "chore: auto-generate changelog"
git push
```

## Lưu ý

- **Script chỉ nhận biết Version: lines được thay đổi**
  - Phải edit `plug.php` → Version: X.Y.Z khác
  - Commit message không quan trọng
  
- **Cần setup git history:**
  - `fetch-depth: 0` trong GitHub Actions (đã config)
  - Local cần full git history

- **Min version filter:**
  - Script chỉ output version > 2.4.7
  - Dates > 2026-03-27
  - Có thể edit trong `generate_changelog.py`

## Troubleshoot

**❌ "No release boundaries found"**
- Nguyên nhân: Không có Version: change trong history
- Fix: Commit version change trước

**❌ "No release boundaries found on current branch"**
- Nguyên nhân: Version changes không trên dev branch
- Fix: Merge PR vào dev, tag version

**✅ Kiểm tra history:**
```bash
git log -p --follow -- plug.php | grep -A2 "Version:"
```
