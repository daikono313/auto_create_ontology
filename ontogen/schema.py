"""オントロジーのデータモデル（Palantir Foundry の Object / Property / Link / Action に準拠）。"""

from typing import Literal

from pydantic import BaseModel, Field

PropertyType = Literal["string", "integer", "decimal", "boolean", "date", "datetime", "url", "enum"]
Cardinality = Literal["one_to_one", "one_to_many", "many_to_one", "many_to_many"]


class Evidence(BaseModel):
    url: str = Field(description="根拠となるページのURL")
    quote: str = Field(description="ページ本文からの逐語引用（短く）")


class Property(BaseModel):
    name: str = Field(description="snake_case の英語名")
    type: PropertyType
    description: str
    enum_values: list[str] = Field(default_factory=list, description="type=enum のときの取りうる値")
    evidence: list[Evidence] = Field(default_factory=list)


class ObjectType(BaseModel):
    id: str = Field(description="PascalCase の英語名（単数形）")
    description: str
    primary_key: str | None = Field(default=None, description="主キーになりそうなプロパティ名")
    properties: list[Property] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)


class LinkType(BaseModel):
    id: str = Field(description="snake_case の関係名（例: belongs_to）")
    source: str = Field(description="起点の ObjectType.id")
    target: str = Field(description="終点の ObjectType.id")
    cardinality: Cardinality = Field(description="source から見た多重度")
    description: str
    evidence: list[Evidence] = Field(default_factory=list)


class ActionType(BaseModel):
    id: str = Field(description="PascalCase の動詞句（例: AddToCart）")
    description: str
    actor: str | None = Field(default=None, description="実行主体（ObjectType.id または役割名）")
    affects: list[str] = Field(default_factory=list, description="作成・更新される ObjectType.id")
    evidence: list[Evidence] = Field(default_factory=list)


class Ontology(BaseModel):
    domain: str = Field(description="対象ビジネスのドメイン名")
    summary: str = Field(description="ビジネスとオントロジー全体の要約")
    object_types: list[ObjectType] = Field(default_factory=list)
    link_types: list[LinkType] = Field(default_factory=list)
    action_types: list[ActionType] = Field(default_factory=list)
    open_questions: list[str] = Field(
        default_factory=list,
        description="サイトからは判断できず、顧客ヒアリングで確認すべき事項",
    )
