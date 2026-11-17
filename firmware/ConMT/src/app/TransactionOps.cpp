#include "TransactionOps.h"
#include "../core/Flash.h"
#include <string.h>
namespace conmt {
template<class T> static T load(const uint8_t* data) { T value; memcpy(&value,data,sizeof(value)); return value; }
static Status copyText(Repository& repo,const Key& source,const Key& destination,bool optional) {
    char text[65]; Status st=repo.text(source,text,sizeof(text));
    if(st==Status::Missing&&optional) return Status::Ok;
    return st==Status::Ok?repo.putText(destination,text,sizeof(text)):st;
}
Status applyTransaction(Repository& repo,ClockPort& clock,const TxStep* steps,uint8_t count,
                        const Entity& source,const Entity& destination,const void* values) {
    for(uint8_t i=0;i<count;++i) {
        TxStep step=flashValue(steps+i);
        Entity target=destination;
        if(step.target==TxTarget::Source) target=source;
        if(step.target==TxTarget::User) target={Kind::User,0};
        if(step.target==TxTarget::System) target={Kind::System,0};
        if(step.target==TxTarget::Settings) target={Kind::Settings,0};
        Key to(target.kind,target.id,step.field);
        const uint8_t* data=values?static_cast<const uint8_t*>(values)+step.argument:nullptr;
        Status st=Status::Invalid;
        switch(step.op) {
            case TxOp::Constant: st=repo.putInteger(to,step.argument); break;
            case TxOp::SourceId: st=repo.putInteger(to,source.id); break;
            case TxOp::DestinationId: st=repo.putInteger(to,destination.id); break;
            case TxOp::Integer: st=repo.putInteger(to,load<uint32_t>(data)); break;
            case TxOp::Number: st=repo.putNumber(to,load<Real>(data)); break;
            case TxOp::Time: st=repo.putTime(to,load<uint64_t>(data)); break;
            case TxOp::Now: st=repo.putTime(to,clock.now().wallMs); break;
            case TxOp::Model: st=repo.putModel(target.kind,target.id,*reinterpret_cast<const Fit*>(data)); break;
            case TxOp::Point: st=repo.putPoint(target.kind,target.id,*reinterpret_cast<const Point*>(data)); break;
            case TxOp::Sensors: {
                const TxSample& sample=*reinterpret_cast<const TxSample*>(data);
                st=repo.putSensors(target.kind,target.id,sample.frame,sample.average,sample.time,step.field); break;
            }
            case TxOp::CopyObject: st=repo.copy(source.kind,source.id,target.kind,target.id); break;
            case TxOp::CopyNumber: {
                Real value; st=repo.number(Key(source.kind,source.id,step.field),value);
                if(st==Status::Ok) st=repo.putNumber(to,value);
                break;
            }
            case TxOp::CopyText: st=copyText(repo,Key(source.kind,source.id,step.field),to,false); break;
            case TxOp::CopyUserText: st=copyText(repo,Key(Kind::User,0,step.field),to,true); break;
            case TxOp::CopyUserField:
                st=repo.copyScalar(Key(Kind::User,0,step.field),to);
                if(st==Status::Missing) st=Status::Ok;
                break;
            case TxOp::CopySensors: st=repo.copyScalar(Key(source.kind,source.id,Field(step.argument)),to,53); break;
        }
        if(st!=Status::Ok) return st;
    }
    return Status::Ok;
}
}
