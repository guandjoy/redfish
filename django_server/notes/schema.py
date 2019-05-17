# cookbook/ingredients/schema.py
import graphene
from graphene import relay, ObjectType
from graphene_django import DjangoObjectType
from graphene_django.filter import DjangoFilterConnectionField
from graphql_relay.node.node import from_global_id

from .models import Note, Color
from django.contrib.auth.models import User


# Graphene will automatically map the Category model's fields onto the CategoryNode.
# This is configured in the CategoryNode's Meta class (as you can see below)
class NoteNode(DjangoObjectType):
    class Meta:
        model = Note
        filter_fields = ['title', 'content', 'color', 'pinned']
        interfaces = (relay.Node, )

    @classmethod
    def get_node(cls, info, id):
        # get object by provided id
        try:
            note = cls._meta.model.objects.get(id=id)
        except cls._meta.model.DoesNotExist:
            return None
        # check the ownership
        if info.context.user == note.owner:
            return note
        # different owner. Not allowed
        return None

class UserNode(DjangoObjectType):
    class Meta:
        model = User
        filter_fields = ['username']
        exclude_fields = ('password', 'is_superuser', 'is_staff',)
        interfaces = (relay.Node, )

class ColorNode(DjangoObjectType):
    class Meta:
        model = Color
        filter_fields = ['value']
        interfaces = (relay.Node,)

    @classmethod
    def get_node(cls, info, id):
        try:
            color = cls._meta.model.objects.get(id=id)
        except cls._meta.model.DoesNotExist:
            return None
        return color
        
class Query(object):
    note = relay.Node.Field(NoteNode)
    all_notes = DjangoFilterConnectionField(NoteNode)
    pinned_notes = DjangoFilterConnectionField(NoteNode)
    profile = DjangoFilterConnectionField(UserNode)
    all_colors = DjangoFilterConnectionField(ColorNode)

    def resolve_all_notes(self, info, **kwargs):
        # context will reference to the Django request
        if not info.context.user.is_authenticated:
            return Note.objects.none()
        else:
            return Note.objects.filter(owner=info.context.user)

    def resolve_profile(self, info):
        if info.context.user.is_authenticated:
            return User.objects.filter(username=info.context.user)

    def resolve_all_colors(self, info):
        return (Color.objects.all())


class AddNote(relay.ClientIDMutation):

    class Input:
        title = graphene.String(required=False)
        content = graphene.String(required=False)

    new_note = graphene.Field(NoteNode)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        if not info.context.user.is_authenticated:
            return None
        note = Note.objects.create(owner=info.context.user, **input)
        return AddNote(new_note=note)

class UpdateNotesColor(relay.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)
        new_color = graphene.String(required=True)

    new_color = graphene.Field(ColorNode)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        local_id = from_global_id(input['id'])[1]
        try:
            note = Note.objects.get(id=local_id, owner=info.context.user)
        except Note.DoesNotExist:
            return None
        color = Color.objects.get(label=input['new_color'])
        note.color = color
        note.save()
        return UpdateNotesColor(color)


class UpdateNote(relay.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)
        color = graphene.String()
        title = graphene.String()
        content = graphene.String()
        pinned = graphene.Boolean()
        order = graphene.Int()

    new_note = graphene.Field(NoteNode)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        local_id = from_global_id(input['id'])[1]
        input.pop('id', None)
        try:
            notes = Note.objects.filter(id=local_id, owner=info.context.user)
        except Note.DoesNotExist:
            return None
        if 'color' in input:
            input['color'] = Color.objects.get(label=input['color'])
        notes.update(**input)
        return UpdateNote(notes[0])


class DeleteNotes(relay.ClientIDMutation):
    class Input:
        ids = graphene.List(graphene.ID, required=True)

    deleted_notes = graphene.List(NoteNode)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        local_ids = [from_global_id(i)[1] for i in input['ids']]
        try:
            notes = Note.objects.filter(id__in=local_ids, owner=info.context.user)
        except Note.DoesNotExist:
            return None
        snapshot = list(notes)
        Note.objects.fill_gaps(notes)
        notes.delete()
        return DeleteNotes(snapshot)


class SwitchPinNotes(relay.ClientIDMutation):
    class Input:
        ids = graphene.List(graphene.ID, required=True)
        action = graphene.String(required=True)

    pinned_unpinned_notes = graphene.List(NoteNode)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        local_ids = [from_global_id(i)[1] for i in input['ids']]
        try:
            notes = Note.objects.filter(id__in=local_ids, owner=info.context.user)
            try:
                first_pinned_order = Note.objects.filter(owner=info.context.user, pinned=True).first().order
                last_pinned_order = Note.objects.filter(owner=info.context.user, pinned=True).last().order
            except AttributeError:
                first_pinned_order = None
                last_pinned_order = None
            try:
                first_not_pinned_order = Note.objects.filter(owner=info.context.user, pinned=False).first().order
            except AttributeError:
                first_not_pinned_order = None
        except Note.DoesNotExist:
            return None

        for index, note in enumerate(notes):
            note.pinned = True if input['action'] == "pin" else False
            note.save()
            new_order = first_not_pinned_order if input['action'] == "pin" else last_pinned_order
            Note.objects.move(note, new_order)

        return SwitchPinNotes(notes)


class Mutation(ObjectType):
    add_note = AddNote.Field()
    update_notes_color = UpdateNotesColor.Field()
    update_note = UpdateNote.Field()
    delete_notes = DeleteNotes.Field()
    switch_pin_notes = SwitchPinNotes.Field()

