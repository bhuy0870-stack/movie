from django.core.management.base import BaseCommand
from main.models import Movie
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
import os

class Command(BaseCommand):
    help = 'Tạo dữ liệu Vector cho TOÀN BỘ phim (Full Database - Chế độ Batch)'

    def handle(self, *args, **kwargs):
        self.stdout.write("⏳ Đang tải mô hình ngôn ngữ (AI)...")
        # Model này hỗ trợ tốt tiếng Việt
        embeddings = HuggingFaceEmbeddings(model_name="keepitreal/vietnamese-sbert")

        self.stdout.write("⏳ Đang quét toàn bộ Database...")
        # LẤY TOÀN BỘ PHIM (Bỏ giới hạn [:1000])
        movies = Movie.objects.all().order_by('-id')
        total_movies = movies.count()
        
        if total_movies == 0:
            self.stdout.write(self.style.WARNING("❌ Không tìm thấy phim nào trong Database!"))
            return

        self.stdout.write(f"🚀 Tìm thấy {total_movies} phim. Bắt đầu 'học' (Sẽ xử lý từng đợt)...")
        
        # Cấu hình xử lý cuốn chiếu (Batch) để không bị tràn RAM
        BATCH_SIZE = 500 
        texts = []
        metadatas = []
        vector_db = None

        for i, m in enumerate(movies):
            # Tạo nội dung phong phú hơn để AI tìm chính xác hơn
            # Bao gồm cả tên gốc, diễn viên (nếu có), quốc gia, năm...
            content = (
                f"Tên phim: {m.title} | "
                f"Tên gốc: {m.origin_name} | "
                f"Thể loại: {m.genres} | "
                f"Quốc gia: {m.country} | "
                f"Năm phát hành: {m.release_date} | "
                f"Nội dung: {m.description}"
            )
            
            texts.append(content)
            metadatas.append({
                "title": m.title,
                "slug": m.slug,
                "poster": m.poster_url or ""
            })

            # Kiểm tra: Nếu gom đủ 500 phim (hoặc là phim cuối cùng) thì xử lý ngay
            if (len(texts) >= BATCH_SIZE) or (i == total_movies - 1):
                percent = round((i + 1) / total_movies * 100, 1)
                self.stdout.write(f"   [{percent}%] Đang mã hóa phim thứ {i+1}/{total_movies}...")
                
                if vector_db is None:
                    # Lô đầu tiên: Tạo mới DB Vector
                    vector_db = FAISS.from_texts(texts, embeddings, metadatas=metadatas)
                else:
                    # Các lô sau: Gộp (Merge) thêm vào DB cũ
                    vector_db.add_texts(texts, metadatas=metadatas)
                
                # Reset bộ nhớ tạm để giải phóng RAM
                texts = []
                metadatas = []

        self.stdout.write("💾 Đang lưu dữ liệu xuống ổ cứng...")
        vector_db.save_local("ai_index")
        
        self.stdout.write(self.style.SUCCESS(f"✅ HOÀN TẤT! AI đã học thuộc lòng toàn bộ {total_movies} phim."))