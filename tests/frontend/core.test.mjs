import test from 'node:test';
import assert from 'node:assert/strict';
import {codePointLength,codePointSlice,sourceSelection,feedbackPayload,missedPayload,stageLabel} from '../../frontend/src/lib/core.mjs';

test('source selection counts Python code points, including non-BMP characters',()=>{
  assert.deepEqual(sourceSelection('A😀B ','秘密',100),{start:104,end:106});
  assert.equal(codePointLength('😀á'),2);
  assert.equal(codePointSlice('A😀B',1,2),'😀');
});
test('manual selection rejects empty and excessive ranges',()=>{
  assert.throws(()=>sourceSelection('','',0));
  assert.throws(()=>sourceSelection('','a'.repeat(1001),0));
});
test('feedback delegates typed actions and revision, never replacement text',()=>{
  assert.deepEqual(feedbackPayload(2,'D000001','CONFIRM_PII','local','reason'),{
    expected_revision:2,finding_id:'D000001',action:'CONFIRM_PII',reviewer_id:'local',reason:'reason'});
  const payload=missedPayload(3,5,{start:10,end:20,text:'private'},'PERSON','local','');
  assert.equal(payload.reason,null);assert.equal(payload.start,10);assert.equal(payload.end,20);
  assert.ok(!('text' in payload));assert.ok(!('replacement_text' in payload));
});
test('stage labels use actual backend operation names',()=>{
  assert.equal(stageLabel('artifact_verification'),'Artifact verification');
  assert.equal(stageLabel('detection'),'PII detection');
});

