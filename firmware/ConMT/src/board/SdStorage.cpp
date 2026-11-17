#include "SdStorage.h"
#ifdef ARDUINO
namespace conmt {
Status SdStorage::failed(Status fallback) { ready_=false; return card_.errorCode()?Status::IoError:fallback; }
Status SdStorage::begin(uint8_t cs,uint8_t rate) {
    ready_=false; configured_=true; cs_=cs; rate_=rate;
    index_.close();
    if(file_.isOpen()) file_.close();
    if(!card_.init(rate,cs)) return Status::Absent;
    if(!volume_.init(&card_)) return Status::Corrupt;
    SdFile root;
    if(!root.openRoot(&volume_)) return Status::IoError;
    if(!file_.open(&root,"CMT.JRN",O_CREAT|O_RDWR)) { root.close(); return Status::IoError; }
    index_.open(root); root.close();
    ready_=true; return Status::Ok;
}
Status SdStorage::size(uint32_t& n) { if(!ready_) return Status::Absent; n=file_.fileSize(); return Status::Ok; }
Status SdStorage::read(uint32_t at,uint8_t* b,uint16_t n) {
    if(!ready_) return Status::Absent;
    if(at>file_.fileSize() || n>file_.fileSize()-at) return Status::Corrupt;
    if(!file_.seekSet(at)||file_.read(b,n)!=n) return failed();
    return Status::Ok;
}
Status SdStorage::write(uint32_t at,const uint8_t* b,uint16_t n) {
    if(!ready_) return Status::Absent;
    file_.clearWriteError();
    if(!file_.seekSet(at)||file_.write(b,n)!=n||file_.getWriteError()) return failed(Status::Full);
    return Status::Ok;
}
Status SdStorage::truncate(uint32_t n) { if(!ready_) return Status::Absent; if(!file_.truncate(n)) return failed(); return Status::Ok; }
Status SdStorage::sync() { if(!ready_) return Status::Absent; if(!file_.sync()) return failed(); return Status::Ok; }
}
#endif
